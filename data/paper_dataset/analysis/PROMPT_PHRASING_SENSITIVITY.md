# Prompt-Phrasing Sensitivity Diagnostic

## Research Question

Does a meaning-preserving change to the judge instruction alter the verdict on
an otherwise identical debate?

## Design

The diagnostic uses 12 fixed different-position debates from the curated
dataset. The sample includes two debates per unordered model pair, covers all 10
topics, and is balanced for Model1 position, starting model, and whether
Position A starts.

Each transcript is evaluated under two judge instructions:

1. The canonical instruction asks an impartial judge to select which model
   argued its assigned position better using argument quality, responsiveness,
   factual discipline, and persuasive clarity.
2. A paraphrase asks a neutral reviewer to choose the model with stronger
   advocacy using reasoning quality, engagement, care with factual claims, and
   clarity of persuasion.

The transcript, position assignment, candidate labels, JSON schema, temperature
(0.1), and output limit (220 tokens) are held fixed. Prompt order alternates
across debates. Gemma-4-31B-IT and Qwen3-30B-A3B-Instruct-2507 complete all
calls, giving 48 judgments and 24 paired comparisons. GLM-4.7 was attempted but
excluded because repeated timeouts and HTTP 500 errors prevented completion of
the paired sample.

## Results

| Judge | Pairs | Exact agreement | Decisive reversals | Tie transitions |
| --- | ---: | ---: | ---: | ---: |
| Gemma-4-31B-IT | 12 | 7 (58.3%) | 1 | 4 |
| Qwen3-30B-A3B-Instruct-2507 | 12 | 7 (58.3%) | 1 | 4 |
| **All completed judges** | **24** | **14 (58.3%)** | **2** | **8** |

Verdict counts also change modestly between prompts:

| Prompt | Model1 wins | Model2 wins | Ties |
| --- | ---: | ---: | ---: |
| Canonical | 7 | 7 | 10 |
| Paraphrased | 5 | 7 | 12 |

The two decisive reversals occur on the criminal-justice and exploration-priority
topics. The remaining eight changes move between a decisive winner and a tie.

## Interpretation

The observed verdict is not invariant to the tested prompt wording: 10 of 24
paired comparisons change. Most changes involve the tie boundary, but two
comparisons reverse the selected model while remaining decisive. The identical
58.3% agreement rate for both judges shows that the effect is not confined to
one evaluator in this small sample.

This is a diagnostic rather than a causal estimate of prompt sensitivity. One
API draw per wording cannot distinguish wording effects from residual
nondeterminism, even at low temperature. A confirmatory run should repeat each
prompt-condition pair several times and include GLM-4.7 when the endpoint is
stable.
