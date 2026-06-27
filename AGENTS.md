# Agent Notes

## Repo Shape
- This is a small Python CLI benchmark, not a package; main entrypoints are `run_conversation.py`, `run_benchmark.py`, and `analyze_results.py`.
- There is no CI, test runner, formatter, or typechecker config; use `python -m py_compile "run_conversation.py" "run_benchmark.py" "analyze_results.py"` as the basic syntax check.
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
- Batch runs support `--benchmark-mode single|paired|permutations`; default is `paired` for `--model-a/--model-b` and `permutations` when `--models` is provided.
- The legacy flag `--no-side-swap` now forces `single` mode for backward compatibility.
- Use `--judge-mode winner_only|detailed|both`; `both` judges the same transcript twice so `analyze_results.py` can report judge-mode agreement.
- Mixed-provider runs are supported with model prefixes like `ollama:llama3.2:3b` and `openai:gemma-4-31b-it`; result rows store provider columns for each role and judge.
- Use `--judge-models` for multiple judges; this multiplies judge calls by `debates * judge_models * judge_modes`.
- With `--models`, permutation mode runs all ordered model-role pairs, so use `--dry-run` first to avoid unexpected API cost.
- Moderator start styles are defined in `START_PROMPTS` in `run_conversation.py`; benchmark uses comma-separated `--start-styles`.

## Outputs
- Transcripts are written to `results/conversations/`; benchmark CSV/JSON and analysis files are written to `results/`.
- Generated `results/**/*.json`, `results/**/*.csv`, and `results/**/*.md` are ignored; only `.gitkeep` placeholders should be tracked there.
- `analyze_results.py` reads the newest `results/*_results.csv` or `results/*_results.json` when `--input` is omitted.

## Focused Verification
- Validate topic loading and planned benchmark runs without API calls: `python run_benchmark.py --topic-ids ai_assignments,remote_work --start-styles neutral,evidence --dry-run`.
- Validate mixed local/cloud planning: `python run_benchmark.py --topic-id ai_assignments --benchmark-mode single --model-a ollama:llama3.2:3b --model-b openai:qwen3-30b-a3b-instruct-2507 --judge-model openai:gemma-4-31b-it --judge-mode winner_only --dry-run`.
- Cheap real API smoke test: `python run_benchmark.py --topic-id ai_assignments --start-styles evidence --no-side-swap --turns 2 --max-tokens 120`.
- Verify aggregate analysis on an existing result: `python analyze_results.py --input results\<run_id>_benchmark_results.csv`.

## Coupled Changes
- If result CSV/JSON columns change in `run_benchmark.py`, update `analyze_results.py`, README analysis docs, and this file in the same change.
- If topic schema or `DiscussionCase` changes, update both `run_conversation.py` and `run_benchmark.py`; benchmark imports topic loading from `run_conversation.py`.
- Keep current framing as symmetric `Position A`/`Position B`; do not reintroduce current-design prose that says simple `FOR`/`AGAINST`.
