# Analysis of the Curated Debate and Judgement Datasets

## Scope

This analysis follows the experiment structure specified by Gerrit: Dataset I contains the generated debates, Dataset II Mode 1 evaluates opposing positions, and Dataset II Mode 2 compares models defending the same position. The analysis uses only the three curated CSV files and does not add new model generations or judge calls.

The validated design contains 240 four-round debates: 10 topics x 6 unordered model pairs x 2 position assignments x 2 starting models. All debates have eight alternating messages. Mode 1 contains 720 judge evaluations. Mode 2 contains 1,440 evaluations representing 240 substantive comparisons shown in both candidate orders.

## Experiment 1: Same-Position Versus Different-Position Ranking

The clearest comparison is the aggregate model ranking under the two evaluation modes. Models are ranked by tie-adjusted win rate, `(wins + 0.5 x ties) / evaluations`, after pooling the three cloud judges. Rank 1 is best.

| Model | Different-position rank | Same-position rank | Absolute change |
| --- | --- | --- | --- |
| meta-llama-3.1-8b-instruct | 1 | 4 | 3 |
| qwen3-30b-a3b-instruct-2507 | 2 | 2 | 0 |
| gemma-4-31b-it | 3 | 1 | 2 |
| apertus-70b-instruct-2509 | 4 | 3 | 1 |

The mean absolute rank change across the four models is 1.5 places. Meta-Llama changes most, moving from rank 1 under different-position evaluation to rank 4 under same-position evaluation. Gemma moves from rank 3 to rank 1, Qwen remains rank 2, and Apertus moves from rank 4 to rank 3. This rank table is more interpretable than a correlation computed from only four models and should be the primary Experiment 1 result.

Ties are uneven across modes: 164 of 720 different-position evaluations (22.8%) and 4 of 1,440 same-position evaluations (0.3%). The ranking uses a fixed half-win treatment for ties, but the difference in tie frequency must be reported because it can affect cross-mode comparisons. These are LLM-judge rankings, not human-validated persuasion rankings.

## Experiment 2: Biases in persuasion judging

### Position and speaking order

Across all 720 different-position judge evaluations, Position A wins 303, Position B wins 253, and 164 are ties. Position A receives 54.5% of decisive verdicts, with a transcript-cluster bootstrap interval of [50.4%, 58.7%].

The starting speaker receives 45.5% of decisive verdicts, with a transcript-cluster bootstrap interval of [41.3%, 49.6%]. Because each debate has eight alternating messages, the non-starting model also gives the final message. This estimate therefore contrasts starting with closing position; it cannot identify which mechanism causes the difference.

| Judge | Position A share | Starting-speaker share |
| --- | --- | --- |
| all judges | 0.545 | 0.455 |
| gemma-4-31b-it | 0.457 | 0.504 |
| glm-4.7 | 0.525 | 0.475 |
| qwen3-30b-a3b-instruct-2507 | 0.630 | 0.397 |

The position effect is judge-dependent: Qwen favors Position A in 63.0% of decisive evaluations, compared with 45.7% for Gemma and 52.5% for GLM. Candidate order is also consequential in Mode 2. Qwen changes the winning model in 149 of 240 candidate-order reversals; this belongs with the Experiment 2 bias diagnostics, not the primary mode-ranking result.

The position and speaking-order swaps use fresh model generations. A verdict change can therefore reflect generation variation as well as the manipulated design factor, so these are design-level sensitivity estimates rather than isolated causal judge-bias coefficients.

### Verbosity

Following Gerrit's requested summary, the two evaluation modes are pooled and one row is reported per judge. Variance is the sample variance in squared words.

| Judge | Decisive | Winner mean | Winner variance | Loser mean | Loser variance |
| --- | --- | --- | --- | --- | --- |
| gemma-4-31b-it | 603 | 639.0 | 2344.4 | 621.1 | 5284.3 |
| glm-4.7 | 720 | 635.3 | 2584.8 | 623.9 | 5202.9 |
| qwen3-30b-a3b-instruct-2507 | 669 | 639.4 | 2971.1 | 619.6 | 4831.4 |

This is observational: length is chosen by the debating model and may correlate with model identity, topic, and argument quality. It does not isolate a causal verbosity bias.

### Judge self-preference

The two judges that also appear as debaters are summarized across both modes. A self-win means that the judge selected its own model as better than the competing model; ties are not counted as self-wins.

| Model acting as judge | Comparisons involving itself | Selected itself | Self-win rate |
| --- | --- | --- | --- |
| gemma-4-31b-it | 360 | 217 | 60.3% |
| qwen3-30b-a3b-instruct-2507 | 360 | 188 | 52.2% |

This descriptive rate mixes possible self-preference with each judge's stable evaluation criteria. It is a diagnostic, not a causal estimate of self-bias.

### Ideological preference

The current topics are not annotated on an ideological scale. The files support judge-specific position preferences, but not a defensible claim about ideological preference.

## Experiment 3: Difficulty of debate positions

To keep the presentation compact, the table reports the four topics with the largest observed departure from a 50/50 split. Counts pool the three judges.

| Topic | Favored position | Position A share | A wins | B wins | Ties |
| --- | --- | --- | --- | --- | --- |
| energy_transition_infrastructure | Position B | 31.0% | 18 | 40 | 14 |
| mega_event_hosting | Position A | 63.0% | 34 | 20 | 18 |
| cultural_repatriation | Position A | 62.3% | 38 | 23 | 11 |
| exploration_priority | Position A | 61.8% | 34 | 21 | 17 |

Energy infrastructure is the strongest current numerical asymmetry: Position B wins 40 decisive evaluations versus 18 for Position A. However, the ten-topic dataset contains no deliberately obvious moral-control item such as the torture example Gerrit suggested. A strong extreme-case demonstration therefore cannot be claimed from the present files and should be added as a pre-specified topic in a future iteration.

## Paper-Ready Summary

1. The primary Experiment 1 result is a direct rank comparison: Meta-Llama falls from first to fourth, Gemma rises from third to first, Qwen remains second, and Apertus rises from fourth to third. The mean absolute movement is 1.5 rank places.
2. Position, speaking order, and candidate order belong under Experiment 2. Their effects vary substantially across judge models.
3. Pooled verbosity summaries show the observed word counts of winners and losers, but cannot establish an independent length preference.
4. Gemma selects itself in 217 of 360 relevant evaluations (60.3%); Qwen does so in 188 of 360 (52.2%).
5. The current strongest position-difficulty example is energy infrastructure. A deliberately extreme moral-control topic remains to be generated.

## Recorded Follow-Ups

These items are recorded for later iterations; they are not required before the first paper revision.

- Consider a forced-choice re-judging pass to remove ties, while preserving the original judgments and documenting the changed protocol.
- Add one or more pre-specified, strongly asymmetric control topics. Gerrit should confirm the exact wording before generation.
- Run controlled matched-length or shortened-argument comparisons before making a causal verbosity claim.
- Add controlled style variants and ideological annotations only if those analyses remain in the final paper scope.

## Interpretation Boundaries

- The outcomes are preferences of three LLM judges, not measurements of human persuasion.
- The same-position file contains 480 presentations but only 240 underlying comparison conditions.
- The current rank comparison is descriptive and is sensitive to the treatment of ties.
- Generated factual claims in the debates have not been externally verified.
