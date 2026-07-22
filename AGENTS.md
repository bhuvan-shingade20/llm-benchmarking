# Agent Notes

## Repo Shape
- This is a small Python CLI benchmark, not a package; main entrypoints are `run_conversation.py`, `run_benchmark.py`, `analyze_results.py`, and `analyze_all_results.py`.
- There is no CI, test runner, formatter, or typechecker config; use `python -m py_compile "run_conversation.py" "run_benchmark.py" "analyze_results.py" "analyze_all_results.py"` as the basic syntax check.
- Dependencies are only `python-dotenv` and `openai` from `requirements.txt`.

## Environment
- Runtime config is loaded from `.env` via `python-dotenv`; never commit `.env` or real API keys.
- Default provider is Ollama; local runs need `ollama serve` plus pulled models such as `llama3.2:3b` and `qwen2.5:3b`.
- SAIA/Academic Cloud uses OpenAI-compatible mode with `LLM_PROVIDER=openai` and `OPENAI_BASE_URL=https://chat-ai.academiccloud.de/v1`.
- Current reliable SAIA judge in docs/tests is `gemma-4-31b-it`; reasoning-style models can return non-JSON text and break judge parsing.

## Topics And Runs
- Saved benchmark cases live in `topics/phase1_topics.json`; each object should have `id`, `question`, `position_a`, and `position_b`.
- `run_conversation.py` accepts either a custom `--topic` with optional `--position-a/--position-b`, or a saved `--topic-id` from the topics file.
- `run_benchmark.py` reads `topics/phase1_topics.json` by default; use `--topic-id` or comma-separated `--topic-ids` for focused runs.
- Batch runs support `--benchmark-mode single|paired|permutations|same_position`; default is `paired` for `--model-a/--model-b` and `permutations` when `--models` is provided.
- Mentor Mode 1 is `single`, `paired`, or `permutations`: one transcript is judged and the judge chooses whether Agent A or Agent B argued better.
- Mentor Mode 2 is `same_position`: `--model-a` is the fixed opponent, candidate models from `--models` argue the same target position in separate debates, and the judge compares which candidate argued that same position better.
- In `same_position`, candidates argue `position_b` by default; use `--same-position-target position_a` to flip the target side.
- The legacy flag `--no-side-swap` now forces `single` mode for backward compatibility.
- Use `--judge-mode winner_only|detailed|both`; `both` judges the same transcript twice so `analyze_results.py` can report judge-mode agreement.
- Use `--evaluation-protocol holistic_persuasion|argument_quality|evidence_fact_check|deliberative_quality|all`; protocols multiply judge calls and allow method-sensitivity comparisons.
- Use `--speaker-order balanced|a_first|b_first`; benchmark default is `balanced`, which runs both first/last-speaker orders to reduce recency bias.
- Mixed-provider runs are supported with model prefixes like `ollama:llama3.2:3b` and `openai:gemma-4-31b-it`; result rows store provider columns for each role and judge.
- Use `--judge-models` for multiple judges; this multiplies judge calls by `debates * judge_models * judge_modes`.
- With `--models`, permutation mode runs all ordered model-role pairs, so use `--dry-run` first to avoid unexpected API cost.
- Moderator start styles are defined in `START_PROMPTS` in `run_conversation.py`; benchmark uses comma-separated `--start-styles`.

## Outputs
- Transcripts are written to `results/conversations/`; benchmark CSV/JSON and analysis files are written to `results/`.
- Generated `results/**/*.json`, `results/**/*.csv`, and `results/**/*.md` are ignored; only `.gitkeep` placeholders should be tracked there.
- `analyze_results.py` reads the newest `results/*_results.csv` or `results/*_results.json` when `--input` is omitted.
- `analyze_all_results.py` aggregates all `results/*_results.csv` files into `results/model_ranking_all_runs.md`, `results/all_model_rankings.md`, and `results/evaluation_protocol_bump_chart.svg`; legacy rows without provider columns should be treated as Academic Cloud/SAIA.
- The all-runs report uses a qualified headline ranking requiring at least 5 valid debates per model, with low-sample models moved to a preliminary table.

## Focused Verification
- Validate topic loading and planned benchmark runs without API calls: `python run_benchmark.py --topic-ids ai_assignments,remote_work --start-styles neutral,evidence --speaker-order balanced --dry-run`.
- Validate mixed local/cloud planning: `python run_benchmark.py --topic-id ai_assignments --benchmark-mode single --model-a ollama:llama3.2:3b --model-b openai:qwen3-30b-a3b-instruct-2507 --judge-model openai:gemma-4-31b-it --judge-mode winner_only --dry-run`.
- Validate protocol comparison planning: `python run_benchmark.py --topic-id ai_assignments --benchmark-mode paired --judge-mode winner_only --evaluation-protocol all --speaker-order balanced --dry-run`.
- Validate same-position Mode 2 planning: `python run_benchmark.py --topic-id ai_assignments --benchmark-mode same_position --model-a openai:qwen3-30b-a3b-instruct-2507 --models openai:apertus-70b-instruct-2509,openai:meta-llama-3.1-8b-instruct --judge-mode winner_only --dry-run`.
- Cheap real API smoke test: `python run_benchmark.py --topic-id ai_assignments --start-styles evidence --no-side-swap --turns 2 --max-tokens 120`.
- Verify aggregate analysis on an existing result: `python analyze_results.py --input results\<run_id>_benchmark_results.csv`.

## Coupled Changes
- If result CSV/JSON columns change in `run_benchmark.py`, update `analyze_results.py`, README analysis docs, and this file in the same change.
- If topic schema or `DiscussionCase` changes, update both `run_conversation.py` and `run_benchmark.py`; benchmark imports topic loading from `run_conversation.py`.
- Keep current framing as symmetric `Position A`/`Position B`; do not reintroduce current-design prose that says simple `FOR`/`AGAINST`.
