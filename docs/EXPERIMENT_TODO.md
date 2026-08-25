# Remaining Experiment Checklist

This document is the single source of truth for experimental work that is not
complete in the current paper dataset. Completed analyses belong in the curated
analysis report; this file contains only pending or in-progress work.

## Priority Experiments

### 1. Prompt-Phrasing Sensitivity

- [x] Re-judge a pre-specified, balanced subset of existing debates with two
  semantically equivalent judge prompts.
- [ ] Complete the paired sample with GLM-4.7. Repeated timeouts and HTTP 500
  errors prevented completion on 2026-08-25.
- [x] Use identical transcripts, candidate
  labels, output schema, and decoding settings for both prompt variants.
- [x] Report exact winner agreement, decisive winner reversals, tie transitions,
  and results by judge.
- [x] Treat the result as a diagnostic because one sample per prompt cannot
  fully separate wording sensitivity from residual API nondeterminism.

The completed two-judge diagnostic is reported in
data/mentor_curated_2026-08-19/analysis/PROMPT_PHRASING_SENSITIVITY.md. It finds
14/24 exact agreements (58.3%), two decisive reversals, and eight tie
transitions. A repeated, three-judge confirmatory run remains pending.

### 2. Forced-Choice Evaluation Without Ties

- [ ] Preserve the original judgments and re-judge the same comparisons with a
  forced-choice winner schema.
- [ ] Report how previously tied cases are resolved and whether model rankings
  change.
- [ ] Apply the same no-tie protocol to both different-position and
  same-position evaluation.

This requires new judgments but no new debates.

### 3. Six-Model Balanced Panel

- [ ] Add one substantially stronger model and one deliberately weaker model to
  the current four-model set.
- [ ] Fix the exact model versions before generation based on cloud availability
  and a documented capability rationale.
- [ ] Use the same six models as both debaters and judges. Do not use separate
  debate-only and judge-only model panels.
- [ ] Run a dry-run and cost audit before generation. With 10 topics and 6
  models, the existing factorial design produces 600 raw debates.
- [ ] Keep position assignment, speaking order, and candidate presentation order
  balanced exactly as in the current design.

Candidate anchors already supported by pilot evidence are
mistral-large-3-675b-instruct-2512 for the stronger end and tinyllama:1.1b for
the weaker end. Availability, context limits, and reliable judge-schema
compliance must be checked before these identifiers are finalized.

### 4. Easy-Position Controls

- [ ] Add pre-specified topics with one clearly more reasonable position and one
  deliberately difficult position.
- [ ] Freeze the exact wording and selection criteria before any generation.
- [ ] Verify that all judges recover the expected direction while retaining the
  symmetric Position A/Position B representation.
- [ ] Include at least one strong-effect example suitable for qualitative
  inspection.

This requires new debates and new judgments.

## Secondary Experiments

### 5. Repeated-Judgment Stability

- [ ] Re-evaluate identical inputs five times per judge with fixed prompt,
  candidate order, and decoding settings.
- [ ] Report within-judge agreement, verdict entropy, model-rank variation, and
  the fraction of inputs with any winner change.

### 6. Controlled Verbosity

- [ ] Pre-sample 100 debates and create matched-length variants by shortening the
  longer argument without adding new claims.
- [ ] Judge original and length-controlled versions in balanced presentation
  order.
- [ ] Report paired verdict changes rather than inferring causality from natural
  word-count differences.

### 7. Controlled Style

- [ ] Create content-preserving style-normalized transcript variants.
- [ ] Validate semantic preservation before judging.
- [ ] Compare original and normalized verdicts using paired agreement and
  reversal rates.

### 8. Debater Confidence

- [ ] Define and validate an annotation procedure for how confident each debater
  sounds.
- [ ] Keep this construct separate from the judge's self-reported confidence.
- [ ] Test whether perceived debater confidence predicts verdicts after
  controlling for model, topic, position, and order.

### 9. Ideological Preference

- [ ] Pre-register which topics are politically relevant.
- [ ] Obtain independent position annotations on a liberal-to-conservative scale
  and report annotator agreement.
- [ ] Estimate judge-specific ideological preference while controlling for
  debater identity and speaking order.

### 10. Human Validation

- [ ] Evaluate the same cloud judges on the cleaned Debate.org subset with
  withheld human outcomes.
- [ ] Report judge-human agreement, inter-judge agreement, and whether observed
  order or verbosity diagnostics transfer to human-written debates.
- [ ] Add direct human evaluation of a benchmark subset if resources permit.

## Reporting Rules

- Keep local Ollama runs diagnostic unless replicated with cloud judges.
- Do not claim causal bias from observational associations.
- Keep original and follow-up judgments separately versioned.
- Record exact model identifiers, prompts, temperatures, sampling rules, API
  dates, failures, and exclusions for every run.
- Add completed experiment summaries to
  docs/PAPER_EXPERIMENT_RESULTS_INDEX.md and move their status out of this
  checklist.
