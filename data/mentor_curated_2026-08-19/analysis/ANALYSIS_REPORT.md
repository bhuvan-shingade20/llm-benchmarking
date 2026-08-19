# Analysis of the Curated Debate and Judgement Datasets

## Scope and experimental unit

This analysis follows the experiment structure specified by Gerrit: Dataset I contains the generated debates, Dataset II Mode 1 evaluates opposing positions, and Dataset II Mode 2 compares models defending the same position. The analysis uses only the three curated CSV files and does not add new model generations or judge calls.

The raw dataset contains 240 four-round debates over 10 topics and four models. The different-position file contains 240 transcript-level judgement rows and 720 judge evaluations. The same-position file contains 480 rows and 1,440 judge evaluations, but these correspond to 240 substantive comparison conditions, each presented twice with Candidate 1 and Candidate 2 reversed. Model-performance estimates therefore use the balanced presentations, while order-stability calculations explicitly pair the two presentations.

## Coverage of Gerrit's requested experiments

| Requested analysis | Status from these files |
| --- | --- |
| Opposing-position vs same-position ranking | Complete descriptive analysis |
| Agreement between judge models | Complete for the three cloud judges |
| Repeated judgement stability | Partial: candidate-order reversal only |
| Sensitivity to style | Not identifiable; requires controlled variants |
| Position and speaking-order bias | Complete descriptive factorial diagnostic |
| Verbosity bias | Observational diagnostic only |
| Ideological preference | Not identifiable without ideological annotation |
| Self-preference | Diagnostic for Gemma and Qwen |
| Position difficulty | Balanced descriptive estimates with cluster intervals |

## Dataset validation and debate characteristics

- The expected design is complete: 10 topics x 6 unordered model pairs x 2 position assignments x 2 starting models = 240 debates.
- Every topic has 24 debates, every factorial condition occurs once, and all debates contain eight alternating messages, corresponding to four turns per model.
- No duplicate transcript or structural turn failure was found.
- Debate length ranges from 969 to 1507 words (median 1277, mean 1259.2).
- 84 transcripts contain an in-dialogue reference to the legacy labels `ModelA` or `ModelB`. This does not alter the CSV schema, but it is a presentational artifact in the generated text.
- 93 transcripts contain citation-like language such as a named study, report, institution, year, or percentage, despite the generation prompt discouraging unsupported citations. These statements have not been externally fact-checked and should not be treated as evidence supplied by the benchmark.

## Experiment 1: Evaluation design and judge agreement

### Opposing-position versus same-position evaluation

The two modes do not produce the same global ordering. Their aggregate score-based ranking correlation is -0.400. Across the six unordered model pairs, the preferred model changes for 2 pairs (33.3%). This directly supports the paper's methodological claim that model comparison depends on the evaluation design.

| Model | Different-position score | Same-position score | Difference |
| --- | --- | --- | --- |
| apertus-70b-instruct-2509 | 0.312 | 0.481 | 0.169 |
| gemma-4-31b-it | 0.512 | 0.710 | 0.198 |
| meta-llama-3.1-8b-instruct | 0.607 | 0.120 | -0.487 |
| qwen3-30b-a3b-instruct-2507 | 0.568 | 0.689 | 0.121 |

Here, score is `(wins + 0.5 x ties) / evaluations`. All models receive the same number of opportunities within a mode. The same-position rows include both candidate orders, so the score is presentation-order balanced.

The largest change is Meta-Llama: it ranks first in different-position evaluation (score 0.607) but last in same-position evaluation (0.120). The two pairwise reversals are Apertus versus Meta-Llama and Gemma versus Meta-Llama:

| Model 1 | Model 2 | Different-position preference | Same-position preference | Changed |
| --- | --- | --- | --- | --- |
| apertus-70b-instruct-2509 | gemma-4-31b-it | gemma-4-31b-it | gemma-4-31b-it | no |
| apertus-70b-instruct-2509 | meta-llama-3.1-8b-instruct | meta-llama-3.1-8b-instruct | apertus-70b-instruct-2509 | yes |
| apertus-70b-instruct-2509 | qwen3-30b-a3b-instruct-2507 | qwen3-30b-a3b-instruct-2507 | qwen3-30b-a3b-instruct-2507 | no |
| gemma-4-31b-it | meta-llama-3.1-8b-instruct | meta-llama-3.1-8b-instruct | gemma-4-31b-it | yes |
| gemma-4-31b-it | qwen3-30b-a3b-instruct-2507 | gemma-4-31b-it | gemma-4-31b-it | no |
| meta-llama-3.1-8b-instruct | qwen3-30b-a3b-instruct-2507 | qwen3-30b-a3b-instruct-2507 | qwen3-30b-a3b-instruct-2507 | no |

Mode sensitivity by judge is:

| Judge | Rank correlation | Pair changes | Pair-change rate |
| --- | --- | --- | --- |
| all judges | -0.400 | 2 | 0.333 |
| gemma-4-31b-it | -0.400 | 3 | 0.500 |
| qwen3-30b-a3b-instruct-2507 | 0.800 | 2 | 0.333 |
| glm-4.7 | -0.200 | 2 | 0.333 |

### Model performance by mode

Different-position evaluation:

| Model | Evaluations | Wins | Losses | Ties | Score |
| --- | --- | --- | --- | --- | --- |
| meta-llama-3.1-8b-instruct | 360 | 187 | 110 | 63 | 0.607 |
| qwen3-30b-a3b-instruct-2507 | 360 | 159 | 110 | 91 | 0.568 |
| gemma-4-31b-it | 360 | 139 | 130 | 91 | 0.512 |
| apertus-70b-instruct-2509 | 360 | 71 | 206 | 83 | 0.312 |

Same-position evaluation:

| Model | Evaluations | Wins | Losses | Ties | Score |
| --- | --- | --- | --- | --- | --- |
| gemma-4-31b-it | 720 | 511 | 209 | 0 | 0.710 |
| qwen3-30b-a3b-instruct-2507 | 720 | 494 | 222 | 4 | 0.689 |
| apertus-70b-instruct-2509 | 720 | 346 | 373 | 1 | 0.481 |
| meta-llama-3.1-8b-instruct | 720 | 85 | 632 | 3 | 0.120 |

These are descriptive rankings produced by the three selected LLM judges. They are not human-validated persuasion scores.

The majority verdicts tell the same broad story but expose uncertainty more directly. In different-position evaluation, majority winners are Meta-Llama 74, Qwen 46, Gemma 44, Apertus 5, and Tie 23, with 48 rows having no majority. In same-position evaluation, majority winners are Gemma 184, Qwen 183, Apertus 107, and Meta-Llama 6.

Topic leaders also vary by mode:

| Topic | Different-position leader | Same-position leader | Same leader |
| --- | --- | --- | --- |
| agricultural_future | meta-llama-3.1-8b-instruct | gemma-4-31b-it | no |
| criminal_justice_framework | qwen3-30b-a3b-instruct-2507 | qwen3-30b-a3b-instruct-2507 | yes |
| cultural_repatriation | meta-llama-3.1-8b-instruct | gemma-4-31b-it | no |
| de_extinction_ethics | qwen3-30b-a3b-instruct-2507 | gemma-4-31b-it | no |
| digital_media_ownership | gemma-4-31b-it | gemma-4-31b-it | yes |
| economic_safety_net | qwen3-30b-a3b-instruct-2507 | gemma-4-31b-it | no |
| energy_transition_infrastructure | meta-llama-3.1-8b-instruct | qwen3-30b-a3b-instruct-2507 | no |
| exploration_priority | qwen3-30b-a3b-instruct-2507 | gemma-4-31b-it | no |
| mega_event_hosting | meta-llama-3.1-8b-instruct | qwen3-30b-a3b-instruct-2507 | no |
| political_ads | meta-llama-3.1-8b-instruct | qwen3-30b-a3b-instruct-2507 | no |

### Agreement between judge models

In different-position evaluation, only 21 of 240 rows are unanimous (8.7%); 48 rows have three different verdicts. Thus, the selected judge changes the exact verdict on 91.2% of debates. In same-position evaluation, 254 of 480 rows are unanimous (52.9%), no row lacks a majority, and 47.1% are judge-dependent. Same-position comparison is therefore markedly more decisive and judge-consistent in this dataset.

Pairwise exact agreement and Cohen's kappa are reported in the accompanying tables. Kappa is important because raw agreement can be inflated when judges have strongly skewed winner distributions. Judge-level model-ranking correlations are based on only four models and should be read as descriptive diagnostics, not precise population estimates.

| Mode | Judge 1 | Judge 2 | Exact agreement | Kappa |
| --- | --- | --- | --- | --- |
| different | gemma-4-31b-it | qwen3-30b-a3b-instruct-2507 | 0.204 | 0.030 |
| different | gemma-4-31b-it | glm-4.7 | 0.438 | 0.312 |
| different | qwen3-30b-a3b-instruct-2507 | glm-4.7 | 0.333 | 0.198 |
| same | gemma-4-31b-it | qwen3-30b-a3b-instruct-2507 | 0.594 | 0.435 |
| same | gemma-4-31b-it | glm-4.7 | 0.850 | 0.774 |
| same | qwen3-30b-a3b-instruct-2507 | glm-4.7 | 0.615 | 0.463 |

Judge-specific model-ranking correlations are:

| Mode | Judge 1 | Judge 2 | Spearman correlation |
| --- | --- | --- | --- |
| different-position | gemma-4-31b-it | qwen3-30b-a3b-instruct-2507 | -1.000 |
| different-position | gemma-4-31b-it | glm-4.7 | 0.800 |
| different-position | qwen3-30b-a3b-instruct-2507 | glm-4.7 | -0.800 |
| same-position | gemma-4-31b-it | qwen3-30b-a3b-instruct-2507 | 0.200 |
| same-position | gemma-4-31b-it | glm-4.7 | 1.000 |
| same-position | qwen3-30b-a3b-instruct-2507 | glm-4.7 | 0.200 |

### Stability under candidate-order reversal

The 240 paired same-position comparisons allow a direct order-stability check. Each judge saw the same two underlying debates twice, with Candidate 1 and Candidate 2 reversed.

| Judge | Pairs | Same model wins | Winner reversals | Tie transitions | Stable rate | Candidate 1 share |
| --- | --- | --- | --- | --- | --- | --- |
| gemma-4-31b-it | 240 | 190 | 46 | 4 | 0.792 | 0.601 |
| qwen3-30b-a3b-instruct-2507 | 240 | 91 | 149 | 0 | 0.379 | 0.435 |
| glm-4.7 | 240 | 166 | 74 | 0 | 0.692 | 0.637 |

Candidate order has a substantial effect. Gemma and GLM select Candidate 1 in 60.1% and 63.7% of decisive presentations, whereas Qwen selects Candidate 1 in only 43.5%. Qwen reverses the winning model in 149 of 240 paired order swaps. This is a direct presentation-order diagnostic, but it is not a substitute for repeated sampling with an identical prompt and candidate order.

### Style sensitivity

The current CSVs contain no controlled paraphrase or style-only variants. Style sensitivity therefore cannot be estimated from these files without a new experiment. Natural stylistic differences between models are entangled with model identity and argument content.

## Experiment 2: Biases in persuasion judging

### Position, speaking order, and model-slot effects

Across all 720 different-position judge evaluations, Position A wins 303, Position B wins 253, and 164 are ties. Position A receives 54.5% of decisive verdicts, with a transcript-cluster bootstrap interval of [50.4%, 58.7%].

The starting speaker receives 45.5% of decisive verdicts, with a transcript-cluster bootstrap interval of [41.3%, 49.6%]. Because each debate has eight alternating messages, the non-starting model also gives the final message. This estimate therefore contrasts starting with closing position; it cannot identify which mechanism causes the difference.

The aggregate position effect is judge-dependent rather than uniform:

| Judge | Position A share | Starter share | Model 1 share |
| --- | --- | --- | --- |
| gemma-4-31b-it | 0.457 | 0.504 | 0.055 |
| glm-4.7 | 0.525 | 0.475 | 0.233 |
| qwen3-30b-a3b-instruct-2507 | 0.630 | 0.397 | 0.661 |

Qwen gives Position A 63.0% of its decisive verdicts, while Gemma gives it 45.7% and GLM 52.5%. Model 1 receives only 33.8% of all decisive verdicts, but model identities were alphabetically assigned to slots rather than randomized, so this is not an isolated label-bias estimate.

Paired sensitivity after changing one design factor:

| Manipulation | Judge | Pairs | Same winner | Winner reversal | Tie transition | Any-change rate |
| --- | --- | --- | --- | --- | --- | --- |
| position_assignment | gemma-4-31b-it | 120 | 36 | 3 | 49 | 0.433 |
| position_assignment | qwen3-30b-a3b-instruct-2507 | 120 | 37 | 38 | 39 | 0.642 |
| position_assignment | glm-4.7 | 120 | 90 | 30 | 0 | 0.250 |
| speaking_order | gemma-4-31b-it | 120 | 40 | 5 | 37 | 0.350 |
| speaking_order | qwen3-30b-a3b-instruct-2507 | 120 | 52 | 26 | 33 | 0.492 |
| speaking_order | glm-4.7 | 120 | 94 | 26 | 0 | 0.217 |

These paired debates use fresh model generations after a role or order change. A verdict change can reflect generation randomness as well as position or order sensitivity, so the estimates are design-level effects rather than pure judge-bias coefficients.

Model scores by position and starting condition show where the aggregate effects arise:

| Mode | Model | Position A | Position B | Starts | Does not start |
| --- | --- | --- | --- | --- | --- |
| different | apertus-70b-instruct-2509 | 0.339 | 0.286 | 0.281 | 0.344 |
| different | gemma-4-31b-it | 0.603 | 0.422 | 0.511 | 0.514 |
| different | meta-llama-3.1-8b-instruct | 0.619 | 0.594 | 0.583 | 0.631 |
| different | qwen3-30b-a3b-instruct-2507 | 0.578 | 0.558 | 0.486 | 0.650 |
| same | apertus-70b-instruct-2509 | 0.514 | 0.449 | 0.478 | 0.485 |
| same | gemma-4-31b-it | 0.725 | 0.694 | 0.706 | 0.714 |
| same | meta-llama-3.1-8b-instruct | 0.072 | 0.168 | 0.103 | 0.138 |
| same | qwen3-30b-a3b-instruct-2507 | 0.689 | 0.689 | 0.714 | 0.664 |

### Verbosity

| Mode | Judge | Decisive | Longer wins | Winner words | Loser words | Near-matched n |
| --- | --- | --- | --- | --- | --- | --- |
| different-position | gemma-4-31b-it | 127 | 0.349 | 615.400 | 646.000 | 84 |
| different-position | glm-4.7 | 240 | 0.349 | 617.000 | 642.200 | 157 |
| different-position | qwen3-30b-a3b-instruct-2507 | 189 | 0.599 | 640.300 | 618.200 | 116 |
| same-position | gemma-4-31b-it | 476 | 0.580 | 645.300 | 614.500 | 307 |
| same-position | glm-4.7 | 480 | 0.567 | 644.500 | 614.700 | 308 |
| same-position | qwen3-30b-a3b-instruct-2507 | 480 | 0.581 | 639.000 | 620.200 | 308 |

Within the near-matched subset, longer-response win rates range from 38.9% to 53.2% across judges and modes. The direction is not consistent: Qwen favors longer responses in different-position evaluation, while Gemma and GLM favor shorter responses there. The present data therefore do not support a judge-independent verbosity effect.

The longer-response calculation is observational. Models choose their own length, and length may correlate with substantive quality, model identity, and topic. The near-matched subset restricts comparisons to arguments within 10% of each other in length, but it is still not the controlled shortening experiment described in Overleaf.

### Judge self-preference

| Mode | Judge/model | Self-judge rows | Self-judge score | Peer-judge score | Difference |
| --- | --- | --- | --- | --- | --- |
| different-position | gemma-4-31b-it | 120 | 0.408 | 0.565 | -0.156 |
| different-position | qwen3-30b-a3b-instruct-2507 | 120 | 0.475 | 0.615 | -0.140 |
| same-position | gemma-4-31b-it | 240 | 0.833 | 0.648 | 0.185 |
| same-position | qwen3-30b-a3b-instruct-2507 | 240 | 0.583 | 0.742 | -0.158 |

Gemma and Qwen appear both as debaters and judges, permitting a within-transcript diagnostic. A positive difference would be consistent with self-preference; a negative difference indicates that the model's own judge is less favorable than the two peer judges. This comparison still mixes self-preference with stable judge-specific evaluation criteria and should not be presented as a causal estimate.

### Ideological preference

The balanced position assignments permit position-specific summaries by judge and topic, but the dataset does not annotate positions on an ideological scale and does not contain human ground truth. Therefore, the present analysis can identify judge-specific position preferences, not ideological preference in the stronger sense requested in Overleaf. That claim needs an explicitly annotated proposition set and a pre-specified ideological coding scheme.

## Experiment 3: Difficulty of debate positions

| Topic | A wins | B wins | Ties | A share | CI low | CI high |
| --- | --- | --- | --- | --- | --- | --- |
| agricultural_future | 29 | 29 | 14 | 0.500 | 0.373 | 0.627 |
| criminal_justice_framework | 35 | 27 | 10 | 0.565 | 0.452 | 0.690 |
| cultural_repatriation | 38 | 23 | 11 | 0.623 | 0.492 | 0.764 |
| de_extinction_ethics | 25 | 24 | 23 | 0.510 | 0.370 | 0.667 |
| digital_media_ownership | 31 | 21 | 20 | 0.596 | 0.500 | 0.692 |
| economic_safety_net | 29 | 28 | 15 | 0.509 | 0.389 | 0.632 |
| energy_transition_infrastructure | 18 | 40 | 14 | 0.310 | 0.190 | 0.439 |
| exploration_priority | 34 | 21 | 17 | 0.618 | 0.482 | 0.765 |
| mega_event_hosting | 34 | 20 | 18 | 0.630 | 0.517 | 0.750 |
| political_ads | 30 | 20 | 22 | 0.600 | 0.442 | 0.745 |

The full factorial design balances model pair, position assignment, and starting model within every topic. Consequently, each topic's Position A share is already standardized over these factors. The intervals resample complete debate rows and keep the three judge verdicts together. They quantify uncertainty over the generated transcript set, not generalization to arbitrary topics, prompts, judges, or human audiences.

Energy infrastructure is the clearest side-difficulty result: all three judges favor Position B, and Position A receives only 31.0% of decisive evaluations. Agricultural policy is exactly balanced overall and within each judge. Other apparent topic effects are less stable across judge identity; for example, the aggregate Position A advantage on mega-event hosting is produced by GLM and Qwen while Gemma favors Position B.

## Confidence diagnostics

| Mode | Judge | Evaluations | Mean | Median | Min | Max | Zeros | Unique |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| different-position | gemma-4-31b-it | 240 | 0.838 | 0.800 | 0.000 | 1.000 | 1 | 6 |
| different-position | glm-4.7 | 240 | 0.709 | 0.750 | 0.600 | 0.950 | 0 | 8 |
| different-position | qwen3-30b-a3b-instruct-2507 | 240 | 0.910 | 0.950 | 0.850 | 0.950 | 0 | 3 |
| same-position | gemma-4-31b-it | 480 | 0.967 | 1.000 | 0.800 | 1.000 | 0 | 5 |
| same-position | glm-4.7 | 480 | 0.730 | 0.750 | 0.600 | 0.900 | 0 | 7 |
| same-position | qwen3-30b-a3b-instruct-2507 | 480 | 0.948 | 0.950 | 0.000 | 0.950 | 1 | 2 |

Judge confidence is self-reported and uses different value distributions across models. It should be analyzed by judge rather than pooled as if calibrated. Two non-tie verdicts have zero confidence: Gemma on different-position DebateId 62 and Qwen on the same-position comparison DebateId1 1 versus DebateId2 3 for Position B. They are retained because 0.00 is syntactically valid, but they warrant clarification before confidence is used as a paper outcome.

## Paper-ready conclusions supported by the current data

1. Evaluation design matters: opposing-position and same-position evaluation change both model scores and some pairwise preferences.
2. Same-position judgments are substantially more consistent across the three judges than different-position judgments, although they compare different evidentiary objects and should not automatically be called more valid.
3. Judge identity is a major source of variation in different-position verdicts; exact winner agreement is low even though all outputs are parseable.
4. Candidate-order reversal provides a direct robustness check and reveals material presentation-order sensitivity, especially for the Qwen judge.
5. The factorial raw-debate design supports clean descriptive diagnostics for position and speaking order. Those effects must be reported alongside any overall model ranking.
6. The present data support only an observational verbosity analysis and a self-preference diagnostic. Controlled style, shortening, repeated-sampling, and ideologically annotated experiments remain unperformed.

## Interpretation boundaries

- The outcomes are LLM-judge preferences, not measurements of human persuasion or belief change.
- The three judges are not independent human raters, and two also appear as debating models.
- Same-position rows contain paired candidate-order presentations; treating all 480 rows as independent would overstate the effective sample size.
- Debate claims were not externally fact-checked. Citation-like statements in generated text should not be repeated as factual evidence in the paper.
- Topic-level intervals cover transcript variation in this dataset only. With ten deliberately selected topics, they do not establish population-wide effects.
- Confidence values are not calibrated across judge models.

## Clarifications to request before final paper claims

1. Should zero-confidence non-tie judgments be treated as valid low-confidence decisions, or as malformed confidence outputs to be re-judged?
2. For the final paper, should the primary ranking collapse each Candidate 1/2 reversal pair into one comparison unit, or retain both order-balanced presentations while clustering uncertainty by pair? This analysis uses the latter and states the 240-unit effective structure.
3. Does Gerrit want ideological positions pre-annotated by the research team, or should that experiment remain outside the current paper until an annotation protocol is agreed?
