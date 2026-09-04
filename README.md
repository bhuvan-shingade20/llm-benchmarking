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

## Final Report Experiments

Only unfinished work is listed below. The protocol and position sets were
approved and frozen on 2026-09-03, and resumable data collection is active.

### September 15 submission scope

The report will include only experiments that are complete and independently
validated by the writing cutoff. Collection is currently prioritized as:

1. complete six-judge agreement with human outcomes on PoliProp;
2. complete the bounded causal matched-length study on the validated paper
   debates; and
3. retain the completed NeurIPS analyses as the report's benchmark foundation.

The broader six-model replication, prompt/order robustness extension,
political-alignment experiment, and causal tone intervention remain preserved
for the PLOS extension and are described as future work if they are unfinished.
Partial streams are never reported as results.

### Experiment 1: Extended replication of the paper

**Question.** Do the paper's findings persist with a broader model panel, no
ties, identical debater and judge panels, and several deliberately clear
position contrasts?

**Design.** Repeat the paper's different-position and matched same-position
experiments with Apertus-70B, Llama-3.1-8B, Qwen3-30B, Gemma-4-31B,
Qwen3.5-397B as the stronger anchor, and TinyLlama-1.1B as the deliberately
weak anchor. The same six models act as debaters and judges. All new judgments
are forced choices. The original 10 topics are retained and supplemented with
a small pre-specified set of extreme controls in which one proposition is
clearly more defensible.

**Remaining work.**

- [ ] Generate the balanced six-model debates and forced-choice judgments.
- [ ] Report rankings for every judge and evaluation mode, averaged rankings,
  judge agreement, position and speaking-order effects, candidate-order
  sensitivity, verbosity associations, self-preference, and position difficulty.
- [ ] Check whether the original qualitative conclusions replicate rather than
  assuming that they will.

### Experiment 2: Robustness and ablation study

**Question.** Are verdicts stable under small, plausible changes to the judging
procedure?

**Design.** Use a pre-specified balanced subset of 120 saved transcripts. For
each judge and transcript, obtain three canonical judgments, one judgment with
candidate order reversed, and one judgment using a single meaning-preserving
paraphrase of the judging prompt. No new debates are required.

**Remaining work.**

- [ ] Report within-prompt repeat agreement and winner-change rates.
- [ ] Report order-invariant agreement after reversing candidate presentation.
- [ ] Report agreement between the paraphrased prompt and the canonical modal
  verdict.
- [ ] Keep this study deliberately small and avoid searching over many prompt
  variants after observing results.

#### Experiment 2b: Causal length and style interventions

**Question.** Do changes in argument length or tone alter a judge's verdict
when the proposition, claims, evidence, rebuttals, opponent, and speaking order
are held fixed?

**Design.** Reuse the frozen 120-transcript sample and deterministically assign
one focal debater per transcript, balanced across models and candidate slots.
For the length intervention, rewrite only the focal debater's turns so that its
total word count matches the opponent's within a fixed tolerance. Report
compression and expansion cases separately. For the style intervention, create
assertive and cautious versions of the same focal turns at matched length. A
fixed strong rewriter may change wording only: it may not add or remove claims,
evidence, examples, numbers, concessions, or rebuttals. Automated checks, two
independent semantic-preservation verifiers, and a blinded manual audit precede
judging. The same six forced-choice judges evaluate the accepted variants in a
fixed, balanced presentation order.

**Remaining work.**

- [ ] Freeze the transformation prompts, focal-candidate assignment, word-count
  tolerance, semantic-preservation rubric, retry limit, and exclusion rule.
- [ ] Generate and validate the matched-length and paired-tone variants before
  collecting any counterfactual judgments.
- [ ] Report paired changes in focal-candidate selection and winner-flip rates,
  separately for every judge and intervention direction, with transcript-level
  bootstrap uncertainty.
- [ ] Treat the estimates as effects of the accepted text interventions, not as
  universal effects of verbosity or style.

### Experiment 3: Political-position alignment

**Question.** Do judges systematically prefer one region of a political
spectrum, and do debaters perform differently when assigned liberal rather than
conservative positions?

**Design.** Freeze a balanced political topic panel and have three independent
annotators label each proposition on a liberal-to-conservative scale before any
debates are analyzed. Generate the balanced six-model debate panel and use the
same six models as forced-choice judges.

**Remaining work.**

- [ ] Complete independent annotations and report agreement and exclusions.
- [ ] Estimate judge-specific ideological preference while controlling for
  topic, debater identities, proposition assignment, and speaking order.
- [ ] Estimate each debater's relative performance on liberal and conservative
  positions while controlling for opponent, topic, order, and judge.
- [ ] Report uncertainty and avoid interpreting measured behavior as a model's
  personal political belief.

### Experiment 4: Agreement with human judgments

**Question.** How closely do LLM judges agree with human judgments on
real-world debates?

**Design.** Use the 740 PoliProp debates with decisive human-majority outcomes.
Each of the same six judges evaluates every debate once using forced choice.
The 93 human ties remain available for a separate secondary analysis and are
not converted into artificial binary ground truth.

**Remaining work.**

- [ ] Complete all six judge streams on the 740 decisive debates.
- [ ] Report accuracy and bootstrap uncertainty against human-majority outcomes.
- [ ] Report inter-judge agreement, judge-specific error patterns, and
  first-candidate or side-selection rates.
- [ ] Analyze human-tie cases separately, without treating either side as the
  correct answer.

## Dependencies and Execution

The four experiments use separately versioned inputs and outputs.

- Experiment 1 uses 10 original topics plus four frozen extreme controls and a
  pre-specified 840-comparison fixed-opponent same-position sample.
- Experiment 2 requires only a frozen subset of Experiment 1 transcripts; it
  does not depend on completion of Experiment 1 judgments.
- Experiment 3 requires its political position set and annotations to be frozen
  but is otherwise independent of Experiments 1, 2, and 4.
- Experiment 4 uses existing human-written debates and can run independently of
  all generated-debate experiments.

Each experiment must have its own resumable runner, validation step, output
directory, and analysis command. The combined runner is optional convenience,
not a dependency between experiments.

## Final Report Structure

1. Reproduce and extend the paper benchmark with the corrected protocol.
2. Test robustness to repeated judging, candidate order, and prompt wording.
3. Test causal sensitivity to controlled length and tone interventions.
4. Analyze judge and debater behavior across the political spectrum.
5. Validate LLM judges against human judgments on real-world debates.
6. Summarize limitations, uncertainty, provider failures, and scope conditions.

Detailed pending tasks are maintained in
[`docs/FUTURE_EXPERIMENTS.md`](docs/FUTURE_EXPERIMENTS.md). The complete
pre-analysis design is in
[`docs/FINAL_REPORT_EXPERIMENT_PLAN_2026-08-31.md`](docs/FINAL_REPORT_EXPERIMENT_PLAN_2026-08-31.md).

## Deferred Work

The following studies remain outside the core final-report experiments unless
they are explicitly added later:

- [ ] A validated annotation study of perceived debater confidence.
- [ ] Direct human evaluation of a newly collected benchmark subset, subject to
  resources and any required ethics review.

## Data Integrity Rules

- Preserve the original tie-permitting judgments unchanged.
- Keep original, follow-up, and incomplete runs separately versioned.
- Resume by unique experimental key and never overwrite completed observations.
- Record exact models, prompts, decoding settings, API dates, failures, and
  exclusions.
- Validate row counts, balance, labels, uniqueness, and missing values before
  reporting results.
- Do not report partial numerical findings as scientific results.
