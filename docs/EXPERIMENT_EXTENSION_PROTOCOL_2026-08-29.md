# Paper Extension Protocol

Planning status: retained as the protocol record for observations already
started under this design. The current four-experiment structure is defined in
`FINAL_REPORT_EXPERIMENT_PLAN_2026-08-31.md`.

Date frozen: 2026-08-29

This protocol incorporates the requirements received after the initial paper
submission. It supersedes the four-debater/three-judge ideological design in
`FOLLOWUP_EXPERIMENT_PROTOCOL_2026-08-28.md` before any debates from that design
were generated. Partial repeated judgments from 2026-08-28 remain separately
versioned and are not mixed into the primary extension.

## Shared Model Panel

The same six models are used as debaters and judges in the generated benchmark:

1. Apertus-70B-Instruct-2509
2. Meta-Llama-3.1-8B-Instruct
3. Qwen3-30B-A3B-Instruct-2507
4. Gemma-4-31B-IT
5. Qwen3.5-397B-A17B, the stronger capability anchor
6. TinyLlama-1.1B, the deliberately weak capability anchor

The first five use the Academic Cloud OpenAI-compatible endpoint. TinyLlama is
run locally through Ollama. Exact model and provider identifiers are frozen in
`configs/extension_2026_08_29.json`.

All judgments are forced choices. The judge must select one of two candidates;
the output schema has no tie value. Malformed outputs are retried and are never
coerced into a winner without an unambiguous candidate label.
For the local TinyLlama judge, Ollama constrained decoding enforces the same
binary choice as a JSON integer enum; the substantive evaluation prompt is
unchanged.

## Experiment 1: Real-World Human-Debate Validation

### Data

The external dataset is PoliProp, the 833-politics-debate subset introduced by
Rescala et al. (Findings of EMNLP 2024) from the Debate.org corpus of Durmus and
Cardie. It contains manually clarified propositions and released human-majority
labels for argument convincingness.

The released labels contain 317 Pro majorities, 423 Con majorities, and 93 human
ties. The primary benchmark includes all 740 debates with a decisive human
majority. Human ties are retained in the prepared data but are not assigned an
artificial binary ground truth.

To provide identical input within TinyLlama's 2,048-token context, each side is
represented by a deterministic excerpt of at most 450 words. The allocation is
balanced across sides and distributed across all available turns. All six judges
receive the same excerpt.

### Primary Measure

Each of the six judges evaluates all 740 decisive debates once under the
canonical prompt and Pro-first presentation. Primary outcomes are:

- accuracy against the released human-majority winner with a debate bootstrap
  interval;
- pairwise agreement between LLM judges;
- side and first-candidate selection rates.

This produces 4,440 primary model judgments.

### Robustness Sample

A deterministic 120-debate subset contains 60 human-Pro and 60 human-Con
winners. For every judge and debate it adds:

- two additional canonical repetitions in the original presentation order;
- one canonical judgment with candidate order reversed;
- one judgment under a meaning-preserving paraphrase of the judge prompt.

The canonical prompt therefore has three repetitions. Prompt robustness is
compared with the modal canonical verdict, reducing the risk that ordinary
within-prompt nondeterminism is mistaken for wording sensitivity. Measures are
three-repeat stability, mean pairwise repeat agreement, side agreement after
candidate-order reversal, first-candidate selection, and agreement between the
paraphrased judgment and the canonical modal verdict.

The robustness component adds 2,880 judgments, for 7,320 real-world model
judgments in total.

### Ideological Annotation and Analysis

Three blinded annotators independently score the Pro and Con positions from -2
(strongly liberal) to +2 (strongly conservative) in contemporary U.S. policy
discourse. Annotators see the proposition only, not the human outcome or model
verdicts. A debate is used for ideological analysis only when at least two
annotators mark it politically relevant and the median non-neutral scores give
opposing ideological directions.

For accepted debates, analysis reports each judge's conservative-position
selection rate and human-majority agreement separately when the human winner is
liberal or conservative. These are judge-behavior diagnostics, not claims about
the models' political beliefs.

## Experiment 2: Six-Model Generated Ideological Debates

Ten pre-specified U.S. policy topics are balanced so that the liberal position
is Position A on five topics and Position B on five. For each topic, the design
crosses all 15 unordered model pairs with both model-position assignments and
both starting models:

`10 x choose(6, 2) x 4 = 600 debates`.

Every debate contains eight alternating messages, four per model, with a maximum
of 220 generated tokens per message. All six models then judge all 600 debates
using the forced-choice protocol, producing 3,600 judgments.

For each debating model, liberal and conservative performance is matched on
topic, opponent, whether the target model starts, and judge. The primary effect
is conservative-position win rate minus liberal-position win rate, with a
topic-cluster bootstrap interval. Judge ideological preference and self-selection
are reported separately.

## Execution Rules

- All output is append-only and resumable at a unique condition key.
- API work is sequential to avoid provider-wide rate limits.
- Original, partial, and superseded runs remain separately versioned.
- Exact prompts, model identifiers, provider, order, repeat, raw response, and
  timestamps are recorded.
- No partial analysis is presented as a result.
- External source archives remain local and ignored; prepared data record the
  official Zenodo source and CC BY-NC-SA 3.0 license.
