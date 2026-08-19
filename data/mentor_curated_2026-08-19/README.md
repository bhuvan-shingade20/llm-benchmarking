# Curated Debate And Judgement Dataset

Date: 2026-08-19

This folder contains the cleaned CSV files generated for the mentor-reviewed benchmark schema. The files are intended to separate raw debate generation from later judging and analysis.

## Dataset I: Debate Generation

File: `RawDebates.csv`

Schema:

| Column | Meaning |
|---|---|
| `DebateId` | Sequential debate identifier. |
| `Model1name` | First model slot. |
| `Model2name` | Second model slot. |
| `positionA` | Fixed Position A text for the topic. |
| `positionB` | Fixed Position B text for the topic. |
| `Model1Position` | Whether Model 1 argued `A` or `B`. |
| `Model2Position` | Whether Model 2 argued `A` or `B`. |
| `DiscussionPlainText` | Full debate transcript with `Model1:` and `Model2:` turns. |
| `starting` | Which model slot started: `Model1` or `Model2`. |

Design:

| Quantity | Value |
|---|---:|
| Topics (`X`) | 10 |
| Models (`Y`) | 4 |
| Unordered model pairs per topic | 6 |
| Role/start variants per model pair | 4 |
| Raw debates (`N = X * Y(Y-1)/2 * 4`) | 240 |
| Rounds per debate | 4 |
| Model turns per debate | 8 |

The raw dataset is balanced: each topic has 24 debates, each model appears in 120 debates, and each topic/model-pair has the four required role/start variants.

## Dataset II, Mode 1: Different-Position Judgements

File: `judgements/DiffPosJudgements.csv`

Each row corresponds to one raw debate. Judges compare the two opposing positions within the same debate and choose the better-argued model, the winning position, and a confidence value.

| Quantity | Value |
|---|---:|
| Rows | 240 |
| Judges | 3 |
| Judge evaluations | 720 |
| Completed winner/position/confidence cells | 720 / 720 |

Aggregate descriptive counts across all judge evaluations:

| Outcome | Count |
|---|---:|
| Position A wins | 303 |
| Position B wins | 253 |
| Ties | 164 |

Model-level descriptive counts:

| Model | Wins |
|---|---:|
| `meta-llama-3.1-8b-instruct` | 187 |
| `qwen3-30b-a3b-instruct-2507` | 159 |
| `gemma-4-31b-it` | 139 |
| `apertus-70b-instruct-2509` | 71 |

Judge agreement is limited in this mode: all three judges selected the same winner in 21 of 240 rows. This suggests that opposing-position evaluation is sensitive to judge choice and should be reported with judge-level detail rather than as a single uncontested ranking.

## Dataset II, Mode 2: Same-Position Judgements

File: `judgements/SamePosJudgements.csv`

Each row compares two debates where the candidate models argued the same tested position. The design includes both tested positions, both candidate-starting settings, and both ordered candidate model assignments.

Design:

| Quantity | Value |
|---|---:|
| Rows | 480 |
| Judges | 3 |
| Judge evaluations | 1440 |
| Completed winner/confidence cells | 1440 / 1440 |
| `testedPosition = A` rows | 240 |
| `testedPosition = B` rows | 240 |
| `candidateStarting = yes` rows | 240 |
| `candidateStarting = no` rows | 240 |
| Ordered candidate model pairs | 12 |
| Rows per ordered candidate model pair | 40 |

Aggregate descriptive counts across all judge evaluations:

| Model | Wins |
|---|---:|
| `gemma-4-31b-it` | 511 |
| `qwen3-30b-a3b-instruct-2507` | 494 |
| `apertus-70b-instruct-2509` | 346 |
| `meta-llama-3.1-8b-instruct` | 85 |
| Tie | 4 |

Majority winners by row:

| Outcome | Rows |
|---|---:|
| `gemma-4-31b-it` | 184 |
| `qwen3-30b-a3b-instruct-2507` | 183 |
| `apertus-70b-instruct-2509` | 107 |
| `meta-llama-3.1-8b-instruct` | 6 |

Same-position evaluation is more decisive than different-position evaluation in this dataset: all three judges selected the same winner in 254 of 480 rows. The strongest descriptive result is that `gemma-4-31b-it` and `qwen3-30b-a3b-instruct-2507` are close at the top under same-position comparison, while `meta-llama-3.1-8b-instruct` is rarely preferred.

## Validation Summary

The files were checked for:

- Exact headers.
- Expected row counts.
- Sequential and unique `DebateId` values.
- Valid raw debate references from judgement files.
- Balanced topic, model-pair, position, and starting conditions.
- Four-round debate structure with eight alternating model turns.
- Complete judge winner/confidence fields.
- Valid winners and confidence values in `[0, 1]`.
- No duplicate same-position comparison keys.

All checks passed on 2026-08-19.
