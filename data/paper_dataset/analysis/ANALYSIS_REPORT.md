# Analysis of the Curated Debate and Judgement Datasets

## Scope

Dataset I contains the generated debates, Dataset II Mode 1 evaluates models arguing different positions, and Dataset II Mode 2 compares models defending the same position. The primary analyses use only the three curated CSV files. A separately identified prompt-phrasing diagnostic adds new judgments on fixed debates but does not generate new debate text.

The validated design contains 240 four-round debates: 10 topics x 6 unordered model pairs x 2 position assignments x 2 starting models. All debates have eight alternating messages. Mode 1 contains 720 judge evaluations. Mode 2 contains 1,440 evaluations representing 240 substantive comparisons shown in both candidate orders.

## Experiment 1: Same-Position Versus Different-Position Ranking

Models are ranked by tie-adjusted win rate, `(wins + 0.5 x ties) / evaluations`, separately for each judge and mode. The final two columns are arithmetic mean ranks across the three cloud judges. Rank 1 is best; D and S denote different-position and same-position evaluation.

| Model | Gemma D | Gemma S | Qwen D | Qwen S | GLM D | GLM S | Mean D | Mean S |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| apertus-70b-instruct-2509 | 4 | 3 | 1 | 1 | 4 | 3 | 3.00 | 2.33 |
| gemma-4-31b-it | 3 | 1 | 2 | 3 | 2 | 1 | 2.33 | 1.67 |
| meta-llama-3.1-8b-instruct | 1 | 4 | 4 | 4 | 1 | 4 | 2.00 | 4.00 |
| qwen3-30b-a3b-instruct-2507 | 2 | 2 | 3 | 2 | 3 | 2 | 2.67 | 2.00 |

Pooling the underlying judge evaluations gives a mean absolute rank change of 1.5 places. Meta-Llama changes most, moving from rank 1 under different-position evaluation to rank 4 under same-position evaluation. Gemma moves from rank 3 to rank 1, Qwen remains rank 2, and Apertus moves from rank 4 to rank 3. The direct rank table exposes these model-level changes more clearly than a single correlation computed from four models.

Ties are uneven across modes: 164 of 720 different-position evaluations (22.8%) and 4 of 1,440 same-position evaluations (0.3%). The ranking uses a fixed half-win treatment for ties, but the difference in tie frequency must be reported because it can affect cross-mode comparisons. These are LLM-judge rankings, not human-validated persuasion rankings.

### Prompt-phrasing sensitivity diagnostic

A balanced 12-debate subset was re-judged under the canonical judge instruction and a meaning-preserving paraphrase. Gemma and Qwen completed 24 paired comparisons. Exact winner agreement was 14/24 (58.3%); the changes comprised 2 decisive winner reversals and 8 transitions between a winner and a tie. The result is diagnostic because one sample per prompt cannot distinguish wording sensitivity from residual API nondeterminism. Full design and results are in [PROMPT_PHRASING_SENSITIVITY.md](PROMPT_PHRASING_SENSITIVITY.md).


## Experiment 2: Biases in persuasion judging

### Position and speaking order

Across all 720 different-position judge evaluations, Position A wins 303, Position B wins 253, and 164 are ties. Position A receives 54.5% of decisive verdicts, with a transcript-cluster bootstrap interval of [50.4%, 58.7%].

The starting speaker receives 45.5% of decisive verdicts, with a transcript-cluster bootstrap interval of [41.3%, 49.6%]. Because each debate has eight alternating messages, the non-starting model also gives the final message. This estimate therefore contrasts starting with closing position; it cannot identify which mechanism causes the difference.

| Judge | Position A share | Starting-speaker share |
| --- | ---: | ---: |
| all judges | 0.545 | 0.455 |
| gemma-4-31b-it | 0.457 | 0.504 |
| glm-4.7 | 0.525 | 0.475 |
| qwen3-30b-a3b-instruct-2507 | 0.630 | 0.397 |

The position effect is judge-dependent: Qwen favors Position A in 63.0% of decisive evaluations, compared with 45.7% for Gemma and 52.5% for GLM. Candidate order is also consequential in Mode 2. Qwen changes the winning model in 149 of 240 candidate-order reversals; this belongs with the Experiment 2 bias diagnostics, not the primary mode-ranking result.

The position and speaking-order swaps use fresh model generations. A verdict change can therefore reflect generation variation as well as the manipulated design factor, so these are design-level sensitivity estimates rather than isolated causal judge-bias coefficients.

### Verbosity

The two evaluation modes are pooled, with one row reported per judge. Variance is the sample variance in squared words.

| Judge | Decisive | Winner mean | Winner variance | Loser mean | Loser variance |
| --- | ---: | ---: | ---: | ---: | ---: |
| gemma-4-31b-it | 603 | 639.0 | 2344.4 | 621.1 | 5284.3 |
| glm-4.7 | 720 | 635.3 | 2584.8 | 623.9 | 5202.9 |
| qwen3-30b-a3b-instruct-2507 | 669 | 639.4 | 2971.1 | 619.6 | 4831.4 |

This is observational: length is chosen by the debating model and may correlate with model identity, topic, and argument quality. It does not isolate a causal verbosity bias.

### Judge self-preference

For every row involving judge-model X, the self-selection indicator is compared with judgments from models that are not participants in that debate. When two uninvolved judges are available, their binary selections are averaged so every debate receives equal weight. Ties count as non-selections.

| Model acting as judge | Relevant rows | Self-selection rate | Uninvolved-judge baseline | Difference |
| --- | ---: | ---: | ---: | ---: |
| gemma-4-31b-it | 360 | 60.3% | 63.2% | -2.9 pp |
| qwen3-30b-a3b-instruct-2507 | 360 | 52.2% | 65.4% | -13.2 pp |

The pooled data therefore do not show positive self-preference under this diagnostic. This remains descriptive because the judges may apply systematically different evaluation criteria.

### Ideological preference

The current topics are not annotated on an ideological scale. The files support judge-specific position preferences, but not a defensible claim about ideological preference.

## Experiment 3: Difficulty of debate positions

To keep the presentation compact, the table reports the four topics with the largest observed departure from a 50/50 split. Counts pool the three judges.

| Topic | Observationally easier position | Observationally harder position | Easier-position share | Easy wins | Hard wins | Ties |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| Energy infrastructure | Decentralized renewable microgrids | Centralized nuclear fission | 69.0% | 40 | 18 | 14 |
| Mega-event hosting | Multi-country co-hosting | Single-nation hosting | 63.0% | 34 | 20 | 18 |
| Cultural repatriation | Repatriate artifacts and use digital replicas | Retain artifacts in universal museums | 62.3% | 38 | 23 | 11 |
| Exploration priority | Prioritize deep-sea exploration | Prioritize space exploration | 61.8% | 34 | 21 | 17 |

Energy infrastructure is the strongest current numerical asymmetry: Decentralized renewable microgrids wins 40 decisive evaluations versus 18 for Centralized nuclear fission. However, the ten-topic dataset contains no deliberately obvious moral-control item. A strong extreme-case demonstration therefore cannot be claimed from the present files; any such control should be pre-specified before a future generation run.

## Summary of Findings

1. The primary Experiment 1 result is a direct rank comparison: Meta-Llama falls from first to fourth, Gemma rises from third to first, Qwen remains second, and Apertus rises from fourth to third. The mean absolute movement is 1.5 rank places.
2. Position, speaking order, and candidate order belong under Experiment 2. Their effects vary substantially across judge models.
3. Pooled verbosity summaries show the observed word counts of winners and losers, but cannot establish an independent length preference.
4. Gemma and Qwen select themselves less often than uninvolved judges select them on the same debate subsets: -2.9 pp and -13.2 pp, respectively.
5. The current strongest position-difficulty example favors Decentralized renewable microgrids over Centralized nuclear fission. A deliberately extreme moral-control topic remains to be generated.

## Open Experimental Extensions

These extensions address limitations of the current experimental design.

- [ ] Re-judge tied outcomes with a forced-choice, no-tie protocol while preserving the original judgments and documenting the protocol change.
- [ ] Add pre-specified easy control debates with one clearly more reasonable position; define the topic wording and selection criteria before generation.
- [ ] Add one stronger and one weaker model, and use the same six-model set for both debate generation and judgment.
- [x] Run a controlled prompt-phrasing sensitivity diagnostic on fixed transcripts with Gemma and Qwen. Repeated confirmation and GLM completion remain open.
- [ ] Run controlled matched-length or shortened-argument comparisons before making a causal verbosity claim.
- [ ] Add controlled style variants and ideological annotations only if those analyses remain in the final paper scope.

The full prioritized checklist and reporting requirements are maintained in [docs/FUTURE_EXPERIMENTS.md](../../../docs/FUTURE_EXPERIMENTS.md).

## Interpretation Boundaries

- The outcomes are preferences of three LLM judges, not measurements of human persuasion.
- The same-position file contains 480 presentations but only 240 underlying comparison conditions.
- The current rank comparison is descriptive and is sensitive to the treatment of ties.
- Generated factual claims in the debates have not been externally verified.
