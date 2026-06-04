# Model And Judge Performance Notes

This file records early qualitative and quantitative observations from Phase 1. These are preliminary prototype results, not final benchmark conclusions.

## Current Setup

- Provider: Academic Cloud / SAIA OpenAI-compatible API
- Endpoint: `https://chat-ai.academiccloud.de/v1`
- Debate topic used for initial tests: `AI tools should be allowed in university assignments`
- Current Agent A stance: `For`
- Current Agent B stance: `Against`
- Current judge metrics: `argument_quality`, `evidence_specificity`, `rebuttal_strength`, `groundedness`, `stance_consistency`, `adaptability`, `clarity`, `overall_persuasiveness`
- Current recommended judge: `gemma-4-31b-it`, because it is different from the current debaters and should reduce same-model judge bias.

Note: `deepseek-r1-distill-llama-70b` was tested as a judge, but it produced long reasoning text before JSON and did not return a parseable evaluation in the current judging pipeline. It may be useful later if we add model-specific handling for reasoning outputs.

## Runs So Far

| Run | Agent A | Agent B | Judge | Turns | Result | Notes |
|---|---|---|---|---:|---|---|
| Local prototype | `llama3.2:3b` | `qwen2.5:3b` | none | 2 | no judge | Proved the local Ollama conversation loop worked, but responses were generic and sometimes too conciliatory. |
| SAIA first working run | `meta-llama-3.1-8b-instruct` | `qwen3-30b-a3b-instruct-2507` | `qwen3-30b-a3b-instruct-2507` | 2 | Agent B | Agent A was noticeably weaker and more generic. Agent B was more direct and confident. Judge output worked. |
| SAIA stronger Agent A run | `mistral-large-3-675b-instruct-2512` | `qwen3-30b-a3b-instruct-2507` | `qwen3-30b-a3b-instruct-2507` | 4 | Agent B | Agent A became more assertive and concrete, but Agent B still won due to stronger attacks on auditability and assessment validity. |
| SAIA independent judge test | `mistral-large-3-675b-instruct-2512` | `qwen3-30b-a3b-instruct-2507` | `gemma-4-31b-it` | 2 | Agent B | Gemma returned clean JSON and avoided same-model judge bias. It still judged Agent B stronger because Agent B attacked the logging/audit mechanism more effectively. |

Latest saved transcript:

- `outputs/20260605_005351_ai_tools_should_be_allowed_in_university_assignmen.json`
- `outputs/20260605_005351_ai_tools_should_be_allowed_in_university_assignmen.md`

## Latest Judge Scores

Run: `mistral-large-3-675b-instruct-2512` vs `qwen3-30b-a3b-instruct-2507`, judged by `qwen3-30b-a3b-instruct-2507`.

| Metric | Agent A FOR | Agent B AGAINST |
|---|---:|---:|
| argument_quality | 7 | 9 |
| evidence_specificity | 4 | 8 |
| rebuttal_strength | 6 | 9 |
| groundedness | 7 | 9 |
| stance_consistency | 8 | 9 |
| adaptability | 7 | 8 |
| clarity | 8 | 8 |
| overall_persuasiveness | 7 | 9 |

Judge winner: `Agent B`

Judge confidence: `0.85`

## Model Observations

### `meta-llama-3.1-8b-instruct`

- Strengths: fast, reliable for basic conversation, good for smoke tests.
- Weaknesses: weaker debating style, more generic openings, less aggressive rebuttal behavior.
- Current assessment: useful for low-cost prototype testing, not ideal as the main competitive debate model.

### `qwen3-30b-a3b-instruct-2507`

- Strengths: strong rebuttal style, clear attack framing, good structured JSON judging, follows judge schema well.
- Weaknesses: can overstate claims if not tightly prompted; when used as both debater and judge, possible self/model-family bias must be controlled.
- Current assessment: strong candidate for debating and judging, but should not be the only judge when Qwen is also one of the debaters.

### `mistral-large-3-675b-instruct-2512`

- Strengths: more assertive and detailed than Llama 3.1 8B, stronger analogies and implementation proposals.
- Weaknesses: sometimes leans on analogies that the opponent can attack; may propose technical mechanisms that sound plausible but need grounding.
- Current assessment: stronger candidate for Agent A than Llama 3.1 8B. Needs better evidence grounding and sharper attacks to beat Qwen consistently.

### `openai-gpt-oss-120b`

- Observation: returned an empty judge response in one SAIA judge test.
- Current assessment: not reliable as the judge in the current script until tested further. May still work as a debater, but not used in the latest benchmark.

### `gemma-4-31b-it`

- Observation: returned clean structured JSON as judge in a short Mistral-vs-Qwen test.
- Strengths: good schema following, clear metric-level comparison, identified practical weaknesses in both agents.
- Weaknesses: only one short test so far; needs more topics and side-swaps before trusting aggregate judgments.
- Current assessment: best current judge candidate because it is not one of the two debaters and produced parseable output.

## Judge Observations

### `qwen3-30b-a3b-instruct-2507` as judge

- Strengths: returns valid structured JSON, gives detailed metric-level scoring, explains decisive reasons.
- Weaknesses: may reward unsupported technical claims unless explicitly instructed to penalize them. This was improved by adding `groundedness` and `unsupported_claims` tracking.
- Bias risk: current latest run uses Qwen as Agent B and judge, so the result may contain same-model or style bias. Next benchmark step should use multiple judges or a judge that is not one of the debaters.

### `gemma-4-31b-it` as judge

- Strengths: independent from current debaters, returns parseable JSON, gives useful metric-level reasoning.
- Weaknesses: less tested than Qwen judge so far.
- Current recommendation: use Gemma as the default single judge for the next few runs, then add a multi-judge setting.

## Current Lessons

- A stronger model for Agent A improved the FOR side, but model strength alone did not guarantee a win.
- The AGAINST side has an easier persuasive angle on this topic because it can focus on academic integrity, unverifiable cognition, and assessment validity.
- The judge needs groundedness scoring because hallucinated citations or unsupported statistics can sound persuasive.
- To get mentor-ready results, we need repeated runs across topics, side swaps, and multiple judges.

## Next Evaluation Improvements

- Run each topic twice with swapped sides to measure side bias.
- Use at least two judge models and compare agreement.
- Add a structured CSV/JSON results table for all runs.
- Add topic batches instead of one-off prompts.
- Track unsupported claims as a penalty in final persuasiveness score.
