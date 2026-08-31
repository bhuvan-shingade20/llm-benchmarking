# LLM Persuasion Benchmark

This repository contains a controlled benchmark of LLM persuasion in
multi-turn debate, together with the validated dataset, analysis code, and
paper source. The current release compares different-position and matched
same-position evaluation while controlling model roles, proposition assignment,
speaking order, and candidate presentation order.

## Current Release

The validated paper dataset is in [`data/paper_dataset`](data/paper_dataset):

| File | Rows | Purpose |
|---|---:|---|
| `RawDebates.csv` | 240 | Balanced debates across 10 topics and four debaters |
| `judgements/DiffPosJudgements.csv` | 240 | Three-judge evaluation of complete debates |
| `judgements/SamePosJudgements.csv` | 480 | Matched comparisons of models defending the same proposition |

The paper-oriented findings are in
[`data/paper_dataset/analysis/ANALYSIS_REPORT.md`](data/paper_dataset/analysis/ANALYSIS_REPORT.md).
The current paper source is in [`paper`](paper).

## Final Report Plan

Only unfinished work is listed below. No additional experiment should be
started or resumed until this plan and its scope are approved.

Data collection is paused at a resumable checkpoint while this plan is under
review.

### 1. Lock the final protocol

- [ ] Confirm the six-model panel: Apertus-70B, Llama-3.1-8B, Qwen3-30B,
  Gemma-4-31B, Qwen3.5-397B as the stronger anchor, and TinyLlama-1.1B as the
  deliberately weak anchor.
- [ ] Use the same six models as debaters and judges in the definitive generated
  benchmark.
- [ ] Use forced-choice judgments throughout the new experiments; preserve the
  original tie-permitting judgments as a separate preliminary dataset.
- [ ] Confirm whether the final report should reproduce both different-position
  and same-position evaluation with the six-model panel.
- [ ] Freeze prompts, decoding settings, sample sizes, exclusions, and primary
  measures before resuming API calls.

### 2. Complete real-world benchmarking and robustness

- [ ] Finish forced-choice evaluation by all six judges on the 740 PoliProp
  debates with decisive human-majority outcomes.
- [ ] Complete the balanced 120-debate robustness sample with repeated canonical
  judgments, reversed candidate order, and a paraphrased judging prompt.
- [ ] Annotate the ideological direction of the human-written propositions with
  independent annotators and report agreement and exclusions.
- [ ] Report judge-human accuracy, inter-judge agreement, repeated-judgment
  stability, candidate-order sensitivity, prompt-phrasing sensitivity, and
  judge-specific ideological preference.

### 3. Complete the six-model generated benchmark

- [ ] Generate and validate the balanced 600-debate panel across 10 political
  topics, all unordered model pairs, both proposition assignments, and both
  speaking orders.
- [ ] Obtain forced-choice judgments from the same six-model panel.
- [ ] Produce per-judge and averaged model rankings, with uncertainty estimates
  and sensitivity checks rather than a single pooled leaderboard.
- [ ] Estimate whether each model performs differently when defending liberal
  and conservative propositions while controlling topic, opponent, assignment,
  order, and judge.
- [ ] Reassess self-preference by comparing a model's judgment of its own debate
  with judgments from models not participating in that debate.
- [ ] If both evaluation modes are retained, construct and judge the matched
  same-position comparisons from this panel under the same forced-choice rule.

### 4. Add clear-position controls

- [ ] Pre-specify a small set of debates with one clearly more defensible
  proposition and one deliberately difficult proposition.
- [ ] Freeze wording and expected direction before generation.
- [ ] Verify that the judges recover the expected direction and include at least
  one strong qualitative example.

### 5. Validate and write the final report

- [ ] Validate row counts, unique experimental keys, balanced assignments,
  parse success, winner labels, and missing values before analysis.
- [ ] Keep partial or failed runs out of scientific summaries.
- [ ] Structure the report around the protocol comparison, real-world validity,
  robustness, ideological effects, and judge-specific behavior.
- [ ] Prefer concise rankings and effect summaries in the main text; place
  detailed per-topic, per-model, and failure tables in the appendix.
- [ ] Report uncertainty, distinguish observational associations from causal
  effects, and document all exclusions and provider failures.
- [ ] Select representative extreme cases only after quantitative analyses and
  selection criteria are fixed.

### 6. Deferred follow-ups

These analyses are not required before the core final-report experiments above:

- [ ] Controlled verbosity using matched-length transcript variants.
- [ ] Controlled style using meaning-preserving normalized variants.
- [ ] A validated annotation study of perceived debater confidence.
- [ ] Direct human evaluation of a benchmark subset, subject to resources and
  any required ethics review.

## Execution Rules

- All generation and judging stages must be incremental and resumable.
- Completed observations must never be overwritten during retries.
- Original, follow-up, and failed/incomplete runs must remain separately
  versioned.
- Exact model identifiers, prompts, temperatures, API dates, failures, and
  exclusions must be retained with every run.
- Analysis begins only after the relevant stage passes its validation checks.

The detailed frozen designs are documented in
[`docs/EXPERIMENT_EXTENSION_PROTOCOL_2026-08-29.md`](docs/EXPERIMENT_EXTENSION_PROTOCOL_2026-08-29.md)
and [`docs/FOLLOWUP_EXPERIMENT_PROTOCOL_2026-08-28.md`](docs/FOLLOWUP_EXPERIMENT_PROTOCOL_2026-08-28.md).
