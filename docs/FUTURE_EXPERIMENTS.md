# Remaining Experiment Checklist

The top-level [`README.md`](../README.md) is the shareable final-report plan.
This file records the corresponding unfinished experimental tasks in more
detail. Completed pilots and preliminary numerical findings are intentionally
excluded.

## Required Before Resuming

- [ ] Approve the final-report scope and ordering of experiments.
- [ ] Confirm the frozen panel of Apertus-70B, Llama-3.1-8B, Qwen3-30B,
  Gemma-4-31B, Qwen3.5-397B, and TinyLlama-1.1B, and use the same models as
  debaters and judges.
- [ ] Confirm that all new judgments use a forced-choice schema without ties.
- [ ] Decide whether the definitive six-model benchmark includes both
  different-position and matched same-position evaluation.
- [ ] Recheck planned call counts, context limits, model availability, and
  output-schema compliance.

## Core Final-Report Experiments

### Real-world human-debate benchmark

- [ ] Complete all six judge streams on the 740 decisive PoliProp debates.
- [ ] Complete the balanced 120-debate robustness sample.
- [ ] Measure accuracy against human-majority outcomes with bootstrap
  uncertainty.
- [ ] Measure inter-judge agreement and judge-specific error patterns.
- [ ] Measure within-prompt stability across repeated canonical judgments.
- [ ] Measure candidate-order robustness after reversing presentation order.
- [ ] Measure prompt-phrasing robustness against the canonical modal verdict.

### Ideological preference on human-written debates

- [ ] Complete independent ideological annotations of both propositions.
- [ ] Report annotator agreement, political relevance, and excluded cases.
- [ ] Estimate each judge's preference for liberal versus conservative
  propositions while controlling for available debate covariates.
- [ ] Keep judge preference distinct from claims about human persuasion or a
  model's political beliefs.

### Six-model generated benchmark

- [ ] Complete and validate 600 debates across the frozen 10-topic panel.
- [ ] Complete forced-choice judgments using the same six-model panel.
- [ ] Report model rankings separately for each judge and averaged across
  judges, with uncertainty estimates.
- [ ] Estimate model performance by ideological position while controlling for
  topic, opponent, position assignment, speaking order, and judge.
- [ ] Re-estimate self-preference against uninvolved-judge baselines.
- [ ] Measure candidate-order and speaking-order sensitivity under the balanced
  design.
- [ ] If retained in scope, generate matched same-position comparisons and
  analyze them under the same forced-choice protocol.

### Clear-position controls

- [ ] Pre-specify clearly defensible and deliberately difficult propositions.
- [ ] Freeze wording, selection criteria, and expected direction before any
  generation.
- [ ] Run balanced debates and forced-choice judging with the approved panel.
- [ ] Confirm the expected strong effect and select a qualitative example using
  pre-declared criteria.

## Final Analysis and Reporting

- [ ] Run structural validation before calculating any result.
- [ ] Exclude incomplete streams and document every exclusion.
- [ ] Compare real-world validity, robustness, ideological effects, and
  generated-debate rankings without pooling incompatible protocols.
- [ ] Use concise main-text tables and move detailed diagnostics to appendices.
- [ ] Report uncertainty and avoid causal language for observational effects.
- [ ] Update the analysis report only after all primary stages validate.

## Deferred Work

- [ ] Run a matched-length intervention for controlled verbosity.
- [ ] Run meaning-preserving style normalization with semantic validation.
- [ ] Define and validate perceived-debater-confidence annotations.
- [ ] Conduct direct human evaluation only if resources and ethics requirements
  permit it.

## Data Integrity Rules

- Preserve the original tie-permitting judgments unchanged.
- Store follow-up judgments and failed/incomplete attempts separately.
- Resume by unique experimental key and never overwrite completed observations.
- Record exact model identifiers, prompts, decoding settings, API dates,
  failures, and exclusions.
- Do not report partial numerical findings as scientific results.
