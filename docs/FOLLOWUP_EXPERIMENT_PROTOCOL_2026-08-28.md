# Follow-up Experiment Protocol

Planning status: historical protocol. The current four-experiment structure is
defined in `FINAL_REPORT_EXPERIMENT_PLAN_2026-08-31.md`.

Date frozen: 2026-08-28

This document records the design before the follow-up results are analyzed. The
two experiments remain separate from the original paper dataset until their
validation checks pass.

## Experiment A: Repeated-Judgment Stability

### Question

How often does the same cloud judge return the same winner when the debate,
candidate labels, prompt, decoding settings, and presentation order are held
fixed?

### Design

- Fixed inputs: all 240 different-position transcripts in the paper dataset.
- Judges: `gemma-4-31b-it`, `qwen3-30b-a3b-instruct-2507`, and `glm-4.7`.
- Repetitions: five verdicts per transcript and judge.
- Repetition 1: the original curated cloud verdict.
- Repetitions 2--5: four new calls using the identical judging prompt.
- Temperature: 0.1.
- Output limit: 220 tokens.
- Total observations: 240 x 3 x 5 = 3,600.
- New API calls: 2,880.

### Primary Measures

- Fraction of transcript--judge groups with one winner across all five calls.
- Mean pairwise agreement among the ten repeat pairs in each group.
- Mean modal-winner share.
- Normalized verdict entropy over Model 1, Model 2, and tie.
- Agreement between the original verdict and each new repetition.
- Standard deviation and range of each model's rank across repetitions.

Only complete five-repeat groups enter the primary stability estimates. Results
are reported separately for each judge.

## Experiment B: Ideological Persuasion

### Question

Does a debating model's observed persuasive performance differ when it defends
a liberal rather than a conservative position, and do judges differ in which
ideological position they prefer?

The ideological frame is fixed to contemporary United States policy discourse.
No claim is made that these labels transfer to other political contexts.

### Topic Panel and Annotation

- Twenty policy topics span economic, social, institutional, environmental,
  and foreign-policy domains.
- Ten topics place the intended liberal position in Position A; ten place it in
  Position B.
- Position texts differ by at most five words within each topic.
- Three blinded cloud annotators score each position from -2 (strongly liberal)
  to +2 (strongly conservative).
- Annotators do not see the pre-specified ideological mapping.

A topic is accepted only if all three annotations are present, at least two
annotators mark it politically relevant, both positions receive non-neutral
opposing majority labels, and the majority labels match the mapping fixed
before annotation. Debate generation stops automatically if any topic fails.

The annotation models are `gemma-4-31b-it`,
`qwen3-30b-a3b-instruct-2507`, and `apertus-70b-instruct-2509`. Mistral Medium,
Qwen3.5-122B, and GPT-OSS-120B were tested and excluded before full annotation
because their responses did not reliably satisfy the fixed JSON schema.

### Debate and Judgment Design

- Debaters: Apertus-70B, Llama-3.1-8B, Qwen3-30B, and Gemma-31B.
- Twenty validated topics.
- Six unordered model pairs per topic.
- Both model--position mappings and both starting models.
- Eight alternating messages per debate, four per model.
- Maximum 220 tokens per message.
- Raw debates: 20 x 6 x 4 = 480.
- Judges: Gemma-4-31B-IT, Qwen3-30B-A3B-Instruct-2507, and GLM-4.7.
- Different-position judge evaluations: 480 x 3 = 1,440.

### Primary Measures

For every model, the primary contrast is its tie-adjusted outcome while
defending the conservative position minus its outcome while defending the
liberal position. The comparison is matched on topic, opponent, target-model
starting status, and judge. Positive values indicate stronger observed
conservative advocacy; negative values indicate stronger observed liberal
advocacy. Uncertainty is reported with a topic-cluster bootstrap interval.

Judge-specific liberal and conservative win counts are reported separately.
These measurements concern LLM-judge preferences, not human persuasion or a
model's political beliefs.

## Execution and Reliability

All stages are incremental and resumable. Provider-wide HTTP 429 limits were
observed when multiple judge streams ran concurrently, so API work is executed
sequentially by judge with ten-second or longer call delays. Completed rows are
never overwritten. Errors and retry events are retained in per-stage logs.
