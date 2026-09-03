# Final Report Experiment Plan

Date drafted: 2026-08-31

This document separates the final-report work into four independently
executable experiments. It replaces the earlier combined extension sequence as
the current planning document. Existing completed observations remain valid for
the experiment and condition under which they were collected.

## Shared Protocol

The proposed panel is Apertus-70B, Llama-3.1-8B, Qwen3-30B, Gemma-4-31B,
Qwen3.5-397B-A17B as a strong anchor, and TinyLlama-1.1B as a weak anchor. The
same six models serve as debaters and judges wherever debates are generated.
Every new judgment is a forced choice between two candidates. Original
tie-permitting files are retained unchanged and analyzed separately.

Before execution, freeze the debate positions, prompts, candidate labels,
decoding settings, sample rules, exclusions, and primary measures. All runners
must append by unique experimental key, skip completed observations, and
validate outputs before analysis.

## Experiment 1: Extended Replication

### Aim

Repeat the paper's experiments under the corrected model and judgment protocol,
then determine whether the original conclusions replicate.

### Inputs and design

- Original 10-topic panel plus a small approved set of extreme controls.
- Six debater models and the same six judge models.
- All unordered model pairs, both model-to-proposition mappings, and both
  speaking orders.
- Forced-choice different-position judgments.
- Matched same-position judgments, either exhaustive or a balanced sample fixed
  after the call-count audit.

### Primary outputs

- Model rankings for each judge and mode, plus averaged ranks.
- Rank changes between different-position and same-position evaluation.
- Inter-judge agreement and judge-specific differences.
- Position, speaking-order, and candidate-order effects.
- Observational verbosity and self-preference diagnostics.
- Recovery of the pre-specified expected winner on extreme controls.

### Frozen execution decision

The approved panel contains the original 10 topics and four pre-specified
extreme controls. Same-position evaluation uses 840 balanced comparisons. Each
comparison holds the proposition, candidate starting status, and opposing model
fixed, and candidate presentation order is deterministically balanced.

## Experiment 2: Robustness and Ablation

### Aim

Measure whether small changes to the judging procedure alter verdicts.

### Inputs and design

- Balanced 120-transcript subset from Experiment 1.
- Three canonical judgments per transcript and judge.
- One candidate-order reversal.
- One fixed, meaning-preserving paraphrase of the judging prompt.
- Same output schema and decoding settings in all conditions.

### Primary outputs

- Pairwise and modal agreement among canonical repeats.
- Fraction of transcript-judge cases with any winner change.
- Order-invariant agreement after candidate reversal.
- Agreement of the paraphrased prompt with the canonical modal verdict.
- Results separated by judge.

This is intentionally a limited diagnostic, not a search over many possible
prompts.

## Experiment 3: Political-Position Alignment

### Aim

Test whether judge verdicts and debater performance vary systematically with
the ideological direction of the defended proposition.

### Inputs and design

- Balanced set of political topics fixed before generation.
- Three independent annotations of each proposition on a
  liberal-to-conservative scale.
- Six-model balanced debate and forced-choice judge panels.
- Proposition labels hidden from debaters and judges during debate and judging.

### Primary outputs

- Annotator agreement and accepted/excluded topics.
- Judge-specific conservative-versus-liberal selection effects.
- Debater-specific conservative-versus-liberal performance effects.
- Uncertainty intervals with controls for topic, opponent, model assignment,
  speaking order, and judge as applicable.

The analysis describes measured behavior under this topic panel. It does not
infer a model's personal beliefs.

## Experiment 4: Agreement With Humans

### Aim

Evaluate how closely LLM judges reproduce human judgments on real-world debate
data.

### Inputs and design

- PoliProp's 740 debates with decisive human-majority outcomes.
- One forced-choice judgment from each of the six judges per debate.
- The 93 human-tie debates retained for separate secondary analysis.

### Primary outputs

- Accuracy against the human-majority winner with debate-bootstrap intervals.
- Pairwise inter-judge agreement.
- Judge-specific error, side-selection, and first-candidate rates.
- Descriptive results for human-tie cases without assigning binary truth.

## Independence and Execution Order

Experiment 1 started after the extreme controls were approved. Experiment 2
depends only on a frozen subset of Experiment 1 transcripts, not on completed
Experiment 1 judgments. Experiment 3 can run independently after its political
position set is approved and annotated. Experiment 4 is fully independent
because it uses existing human-written debates.

Each experiment will expose a separate runner, output directory, validator, and
analysis command. A combined pipeline may invoke these runners sequentially,
but no experiment will rely on another experiment's process state or partially
written outputs.

## Deferred Analyses

Matched-length verbosity interventions, style normalization, perceived
confidence annotation, and newly collected human evaluation remain outside the
four core experiments unless separately approved.
