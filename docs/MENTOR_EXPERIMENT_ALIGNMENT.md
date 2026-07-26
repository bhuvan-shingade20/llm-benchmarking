# Mentor Experiment Alignment

This compares the mentor's proposed experiment section with the experiments completed so far and identifies what still needs to be run. Future experiments should avoid `ai_assignments` and use dated result folders.

## High-Level Verdict

The mentor's experiment structure is well aligned with our benchmark design, but our current evidence only partially supports it. We have implemented most required mechanisms, and we have pilot results showing design sensitivity, position bias, protocol sensitivity, verbosity bias, and judge parseability problems. We do not yet have enough controlled evidence for final claims about judge agreement, repeated-judgment stability, or ideological preferences.

The current results should be framed as preliminary diagnostics unless rerun with stronger judges and cleaner controls.

## Abstract Claim Check

| Abstract Claim | Current Support | Evidence So Far | Needed Before Paper Claim |
|---|---|---|---|
| Model rankings are sensitive to evaluation protocol. | Partial support | Protocol rankings changed in `baseline_capacity_ladder`; `gemma2:2b` led holistic/deliberative while `qwen2.5:0.5b` led argument/evidence. | Rerun with stronger cloud judge and matched model/topic set. |
| Role and position changes affect results. | Partial support | Paired and balanced local runs showed strong Agent A / Position A effects. | Controlled reversal analysis with verdict-flip rates and stronger judge. |
| Speaking order affects verdicts. | Weak/unclear support | In the latest baseline, `a_first` and `b_first` had the same Agent A split, suggesting label/position bias rather than pure speaking-order bias. Earlier local runs also had strong role artifacts. | Separate first-speaker and final-speaker effects from Agent A label using controlled transcripts or stronger judge. |
| Judges prefer verbosity. | Partial support | Baseline ladder: longer agent won 80 / 126 comparable valid rows. | Matched-length or shortened-argument experiment. |
| Judge models disagree. | Not yet adequately supported | Some multi-judge attempts exist, but local judge parse failures and cloud rate limits make them unreliable. | Fixed transcript set judged by multiple judges; report pairwise agreement and rank correlation. |
| Judges have ideological preferences. | Not yet supported | `political_ads` was included, but not enough controlled ideological-topic and judge-specific reversal evidence. | Run ideological topic panel with model/role/order controls and multiple judges. |
| Some debate positions are easier than others. | Partial support | Strong topic-side patterns: `political_ads` and `de_extinction_ethics` favored Position A; `energy_transition_infrastructure` favored Position B. | Estimate adjusted position effects controlling for model, judge, protocol, speaker order, and length. |

## Mentor Experiment 1: Evaluation Design And Judge Agreement

### 1(a) Comparison Of Evaluation Protocols

Status: partially done.

What we have:

| Completed Piece | Evidence |
|---|---|
| Four evaluation protocols implemented | `holistic_persuasion`, `argument_quality`, `evidence_fact_check`, `deliberative_quality`. |
| Same transcript can be judged under all protocols | `--evaluation-protocol all`. |
| Protocol bump chart implemented | `baseline_capacity_ladder_evaluation_protocol_bump_chart.svg` and previous experiment charts. |
| Opposing-position protocol implemented | `single`, `paired`, and `permutations`. |
| Same-position protocol implemented | `same_position`. |

What is missing:

| Missing Piece | Why It Matters |
|---|---|
| A clean controlled comparison between opposing-position and same-position rankings | Existing Mode 1 and Mode 2 runs were not matched enough for final rank-correlation claims. |
| Pairwise ranking reversals between protocols | Current reports show protocol rankings but do not compute reversal rates. |
| Fraction of model pairs whose preferred model changes | Needs a dedicated analysis script or post-processing table. |

Recommended next run:

```powershell
python run_benchmark.py --topic-ids political_ads,de_extinction_ethics,energy_transition_infrastructure --benchmark-mode permutations --models ollama:qwen2.5:0.5b,ollama:tinyllama:1.1b,ollama:gemma2:2b,ollama:llama3.2:3b --judge-model ollama:qwen2.5:3b --judge-mode winner_only --evaluation-protocol all --speaker-order balanced --turns 2 --max-tokens 70 --dry-run
```

Better paper-grade version: rerun the same design with `openai:gemma-4-31b-it` as judge when quota permits.

### 1(b) Agreement Between Judge Models

Status: not adequately done.

What we have:

| Completed Piece | Limitation |
|---|---|
| `--judge-models` implemented | The code can run multiple judges. |
| Some partial multi-judge local/cloud rows exist | Too many parse failures and rate limits for clean agreement claims. |

What is missing:

| Missing Piece | Needed Output |
|---|---|
| Fixed transcript set judged by multiple judges | Pairwise judge agreement, majority agreement, judge-specific rankings. |
| Rank correlation between judges | Needed for mentor's reporting target. |
| Fraction of verdicts depending on selected judge | Needs per-transcript judge comparison. |

Recommended next run:

```powershell
python run_benchmark.py --topic-ids political_ads,de_extinction_ethics,energy_transition_infrastructure --benchmark-mode paired --model-a ollama:gemma2:2b --model-b ollama:llama3.2:3b --judge-models openai:gemma-4-31b-it,openai:qwen3-30b-a3b-instruct-2507,ollama:qwen2.5:3b --judge-mode winner_only --evaluation-protocol holistic_persuasion --speaker-order balanced --turns 2 --max-tokens 90 --dry-run
```

### 1(c) Stability Across Repeated Judgments

Status: not done.

What is missing:

| Missing Piece | Needed Output |
|---|---|
| Rejudge same transcript multiple times | Within-judge agreement and variance in verdicts. |
| Slight prompt variants | Sensitivity to minimal judge-prompt changes. |
| Temperature-controlled judging | If using stochastic judges, report sampling settings. |

Implementation note: current benchmark reruns debates when rerun, so for this experiment we need either a rejudge-only script or a mode that reads saved transcripts and applies judges repeatedly.

## Mentor Experiment 2: Biases In LLM Persuasion Judging

### 2(a) Position And Speaking-Order Bias

Status: partially done.

What we have:

| Completed Piece | Evidence |
|---|---|
| Model-role swapping | `paired` mode swaps Position A/B model assignment. |
| Speaker-order reversal | `--speaker-order balanced` runs both `a_first` and `b_first`. |
| Bias diagnostics | Reports include position, speaker-order, and length diagnostics. |
| Pilot evidence of label/position bias | Baseline: 92 / 126 valid rows chose Agent A; `a_first` and `b_first` had identical 46/17 splits. |

What is missing:

| Missing Piece | Needed Output |
|---|---|
| Verdict-flip rates under exact reversal pairs | Need compare Debate R1 vs swapped R2 and first vs last speaker. |
| Estimated advantage for position and speaking slot | Need regression or grouped estimate. |
| Stronger judge validation | Local judge artifacts are too large for final claims. |

### 2(b) Verbosity Bias

Status: partially done.

What we have:

| Completed Piece | Evidence |
|---|---|
| Word-count diagnostic | `analyze_all_results.py` counts Agent A/B transcript words. |
| Pilot verbosity signal | Baseline: longer agent won 80 / 126 comparable rows. |

What is missing:

| Missing Piece | Needed Output |
|---|---|
| Matched-length condition | Same model/topic but enforce equal token budget or truncate both sides. |
| Shortened-argument condition | Judge full vs shortened versions of the same argument. |
| Verdict changes caused only by length | Needed to claim verbosity bias independently of quality. |

Implementation note: current code can approximate matched length with tighter `--max-tokens`, but a true shortened-argument condition needs a rejudge/transcript-edit experiment.

### 2(c) Ideological Preference Of Judges

Status: not done.

What we have:

| Completed Piece | Limitation |
|---|---|
| `political_ads` topic included | One topic is not enough to infer ideology. |
| Role swapping implemented | Needs multiple ideological topics and multiple judges. |

Recommended topic panel:

| Topic | Ideological Dimension |
|---|---|
| `political_ads` | Speech moderation vs misinformation control. |
| `criminal_justice_framework` | Restorative vs retributive justice. |
| `economic_safety_net` | Universal basic income vs job guarantee. |
| `cultural_repatriation` | Historical justice vs universal museum preservation. |
| `right_to_be_forgotten` | Privacy/rehabilitation vs public record/accountability. |

Needed output: judge-specific position win rates, role-reversal verdict flips, and differences between judges.

## Mentor Experiment 3: Difficulty Of Debate Positions

Status: partially done.

What we have:

| Completed Piece | Evidence |
|---|---|
| Per-topic side diagnostics | Baseline had large topic-side splits. |
| Multiple complex topics | Latest baseline used `political_ads`, `de_extinction_ethics`, and `energy_transition_infrastructure`. |

What is missing:

| Missing Piece | Needed Output |
|---|---|
| Adjusted position effects | Control for model, judge, protocol, speaker order, and length. |
| Uncertainty intervals | Needed for paper-strength reporting. |
| Consistency across judges and protocols | Needed to distinguish topic difficulty from judge preference. |

Recommended approach: after enough rows are collected, fit a simple logistic model or bootstrap grouped win-rate differences by topic/position.

## Experiments We Added Beyond The Mentor Draft

These should be kept because they make the paper stronger and protect against misleading results.

| Added Experiment | Status | Why Keep It |
|---|---|---|
| Baseline capacity ladder | Done as pilot | Gives weak/simple baselines and shows whether benchmark separates trivial from stronger models. |
| Validity audit | Done | Shows transparency about prompt copying, label bias, and judge parseability. |
| Cloud-judged baseline validation | Not done | Needed to validate surprising local results like `qwen2.5:0.5b` outperforming TinyLlama. |
| Judge parseability/reliability report | Partial | Important because local judges can fail structurally, not just disagree semantically. |
| Topic difficulty map | Partial | Makes paper more readable and interactive by showing which topics are side-biased or ambiguous. |

## Recommended Revised Experiment Section

The mentor's three experiments should remain the core structure. Add one short preliminary experiment before them:

1. Preliminary sanity check: simple baseline ladder and validity audit.
2. Evaluation design and judge agreement.
3. Biases in LLM persuasion judging.
4. Difficulty of debate positions.

This keeps the mentor's suggested structure but adds our new finding: before studying persuasion quality, we must show the benchmark pipeline itself is not dominated by parsing failures, prompt copying, or label bias.

## Immediate Next Runs

Priority order:

| Priority | Experiment | Why Next |
|---:|---|---|
| 1 | Cloud-judge the baseline ladder with `gemma-4-31b-it` | Validates whether current local baseline ranking is real or judge artifact. |
| 2 | Multi-judge agreement on a small fixed topic/model set | Directly addresses mentor Experiment 1(b). |
| 3 | Same-position Mode 2 with both target sides | Completes mentor Experiment 1(a) comparison between opposing-position and same-position protocols. |
| 4 | Matched-length verbosity run | Turns current verbosity diagnostic into causal evidence. |
| 5 | Ideological topic panel with role swaps and multiple judges | Supports or removes the abstract claim about ideological preferences. |
