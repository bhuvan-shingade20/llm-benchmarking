# Remaining Experiment Checklist

This checklist contains only unfinished work for the final report. The four
experiments are defined in the top-level [`README.md`](../README.md) and the
detailed [final-report plan](FINAL_REPORT_EXPERIMENT_PLAN_2026-08-31.md).

## Shared Prerequisites

- [x] Approve the six-model panel and exact model identifiers.
- [x] Approve forced-choice judging for every new experiment.
- [x] Freeze the original-topic extension, extreme-control positions, and
  political-spectrum positions before generation.
- [x] Fix prompts, decoding settings, exclusions, and primary measures.
- [x] Audit API calls, context limits, and schema compliance.
- [x] Provide an independent resumable runner for each experiment.

## Experiment 1: Extended Paper Replication

- [x] Retain the original 10 topics and add the approved extreme controls.
- [ ] Generate balanced six-model debates across model pairs, proposition
  assignments, and speaking orders.
- [ ] Use the same six models as forced-choice judges.
- [ ] Reproduce both different-position and matched same-position evaluation.
- [x] Freeze an 840-comparison balanced same-position sample with a shared
  opponent and matched candidate starting status.
- [ ] Report per-judge and averaged rankings for both modes.
- [ ] Re-evaluate judge agreement, order effects, verbosity associations,
  self-preference, and position difficulty.
- [ ] Verify the expected direction on the extreme controls and select examples
  using pre-declared criteria.

## Experiment 2: Robustness and Ablation

- [x] Freeze a topic-balanced 120-transcript sample rule from Experiment 1.
- [x] Freeze one meaning-preserving paraphrase of the judge prompt.
- [ ] Collect three canonical judgments per transcript and judge.
- [ ] Collect one candidate-order reversal and one prompt-paraphrase judgment.
- [ ] Report repeat agreement, any-winner-change rates, order-invariant
  agreement, prompt agreement, and judge-specific results.
- [ ] Do not add prompt variants after inspecting outcomes.

### Experiment 2b: Causal Length and Style Interventions

- [ ] Freeze the balanced focal-candidate assignment on the same 120
  transcripts without using verdicts.
- [ ] Freeze one rewriter, transformation prompts, decoding settings, target
  lengths, tolerance, retry limit, and exclusion rule before generation.
- [ ] Create a matched-length version by moving only the focal debater to the
  opponent's total word count; retain whether this required compression or
  expansion.
- [ ] Create length-matched assertive and cautious variants of the same focal
  turns while preserving all substantive content.
- [ ] Require structural checks and acceptance by two independent semantic
  verifiers before a variant can enter judging.
- [ ] Complete a blinded manual audit of a pre-specified random subset before
  judging starts.
- [ ] Judge accepted counterfactuals with the same six-model forced-choice panel
  and identical candidate order within each paired comparison.
- [ ] Report paired selection changes, winner flips, judge-specific effects,
  transcript-bootstrap intervals, exclusions, and verifier agreement.
- [ ] Separate compression from expansion and avoid generalizing beyond the
  accepted counterfactual edits.

## Experiment 3: Political-Position Alignment

- [x] Approve and freeze the balanced ten-topic political panel.
- [ ] Obtain three independent ideological annotations per proposition.
- [ ] Report annotation agreement, political relevance, and exclusions.
- [ ] Generate balanced debates using the same six-model panel.
- [ ] Complete forced-choice judging with the same six models.
- [ ] Estimate each judge's relative preference for liberal and conservative
  positions with appropriate controls and uncertainty.
- [ ] Estimate each debater's relative performance on liberal and conservative
  positions with appropriate controls and uncertainty.

## Experiment 4: Human-Judge Agreement

- [ ] Complete six forced-choice judge streams on the 740 decisive PoliProp
  debates.
- [ ] Report accuracy with bootstrap uncertainty against human majorities.
- [ ] Report inter-judge agreement and judge-specific error patterns.
- [ ] Report first-candidate and proposition-side selection rates.
- [ ] Analyze the 93 human-tie cases separately without binary ground truth.

## Final Analysis and Writing

- [ ] Validate each experiment independently before calculating results.
- [ ] Keep incompatible protocols and incomplete streams out of pooled results.
- [ ] Use concise main-text rankings and effect summaries; move detailed tables
  to appendices.
- [ ] Report uncertainty and distinguish observational effects from causal
  claims.
- [ ] Document all exclusions, retries, rate limits, and provider failures.
- [ ] Update the final analysis report only after all four experiments pass
  validation.

## Deferred Work

- [ ] Validated perceived-debater-confidence annotations.
- [ ] Newly collected direct human evaluation, subject to resources and ethics
  requirements.
