# Paper Experiment Results Index

Date: 2026-08-05

This file is the handoff document for turning the benchmark results into paper prose. It lists what was run, where the results are stored, what claims are supported, and what should be treated only as diagnostic evidence.

## How To Use This With Another AI

Give the other AI this file first. The repository intentionally ignores raw result CSV/JSON files and result-folder Markdown reports, so this index is the pushed source of truth for the main numbers and caveats. If the other AI has access to the local workspace or an artifact bundle, it can also read the folder summaries and aggregate reports listed below.

If using only the pushed GitHub repository, ask the other AI to rely on this file plus the tracked code and SVG charts.

Recommended prompt:

```text
You are helping write the experiments/results section of a paper on LLM debate persuasion benchmarking. Use the repository files below as the source of truth. Separate paper-grade cloud evidence from local diagnostic pilot evidence. Do not overclaim unsupported mentor items. Write concise academic prose with tables where helpful.

Read first if available:
1. docs/PAPER_EXPERIMENT_RESULTS_INDEX.md
2. docs/MENTOR_EXPERIMENT_ALIGNMENT.md
3. results/2026-07-25_baseline_capacity_ladder/experiment_summary.md
4. results/2026-07-25_baseline_capacity_ladder/validity_audit.md
5. results/2026-07-26_cloud_judged_baseline_ladder/experiment_summary.md
6. results/2026-08-05_protocol_mode_comparison/experiment_summary.md
7. results/2026-08-05_judge_agreement_local_pilot/experiment_summary.md
8. results/2026-08-05_repeated_judgment_local_pilot/experiment_summary.md
9. results/2026-08-05_style_sensitivity_local_pilot/experiment_summary.md
10. results/2026-08-05_position_order_bias_cloud/experiment_summary.md
11. results/2026-08-05_verbosity_length_local_pilot/experiment_summary.md
12. results/2026-08-05_ideology_self_preference_local_pilot/experiment_summary.md
13. results/2026-08-05_position_difficulty_cloud/experiment_summary.md
```

## Evidence Quality Labels

| Label | Meaning |
|---|---|
| Paper-grade | Cloud-judged, parseable, controlled enough to cite as primary evidence with caveats. |
| Strong diagnostic | Useful evidence, but not enough for a final causal claim. |
| Local diagnostic | Local-only result useful for method/debugging, not final paper-grade model or judge claims. |
| Failed/partial | Important to report as limitation, but not usable as a clean result. |

## Mentor Checklist

| Mentor Item | Status | Evidence Quality | Main Folder |
|---|---|---|---|
| 1(a) Opposing-position vs same-position protocols | Partially completed | Paper-grade but one same-position side partial | `results/2026-08-05_protocol_mode_comparison/` |
| 1(b) Agreement between judge models | Completed as local pilot | Local diagnostic | `results/2026-08-05_judge_agreement_local_pilot/` |
| 1(c) Repeated judgment stability | Completed as local pilot | Local diagnostic | `results/2026-08-05_repeated_judgment_local_pilot/` |
| 1(d) Style sensitivity | Completed as local framing pilot | Local diagnostic | `results/2026-08-05_style_sensitivity_local_pilot/` |
| 2(a) Position and speaking-order bias | Completed with cloud paired run | Paper-grade diagnostic | `results/2026-08-05_position_order_bias_cloud/` |
| 2(b) Verbosity bias | Completed as token-limit pilot | Local diagnostic | `results/2026-08-05_verbosity_length_local_pilot/` |
| 2(c) Ideological preference | Completed as local diagnostic, not clean | Local diagnostic / not conclusive | `results/2026-08-05_ideology_self_preference_local_pilot/` |
| 2(d) Self-preference bias | Included in same local diagnostic, not clean | Local diagnostic / not conclusive | `results/2026-08-05_ideology_self_preference_local_pilot/` |
| 3 Difficulty of debate positions | Completed with controlled cloud design, no regression | Paper-grade diagnostic | `results/2026-08-05_position_difficulty_cloud/` |

## Completed Core Results

### Preliminary Baseline Ladder

Folder: `results/2026-07-25_baseline_capacity_ladder/`

Evidence quality: local diagnostic.

Key findings:

| Result | Value |
|---|---:|
| Planned judge rows | 144 |
| Valid judge rows | 126 |
| Invalid judge rows | 18 |
| Local judge Agent A wins | 92 / 126 |
| Longer response won | 80 / 126 |

Use in paper as a sanity-check and validity audit, not final ranking evidence.

### Cloud-Judged Baseline Ladder

Folder: `results/2026-07-26_cloud_judged_baseline_ladder/`

Evidence quality: paper-grade baseline validation.

Key findings:

| Model | Judge Evaluations | Wins | Losses | Ties | Win Rate |
|---|---:|---:|---:|---:|---:|
| `ollama:gemma2:2b` | 96 | 53 | 7 | 36 | 0.55 |
| `ollama:qwen2.5:0.5b` | 48 | 14 | 0 | 34 | 0.29 |
| `ollama:llama3.2:3b` | 48 | 7 | 5 | 36 | 0.15 |
| `ollama:tinyllama:1.1b` | 96 | 0 | 62 | 34 | 0.00 |

Important interpretation:

| Finding | Interpretation |
|---|---|
| 144 / 144 valid cloud judge rows | Corrected prompt plus `gemma-4-31b-it` solved local parse failures. |
| Position A wins = 37, Position B wins = 37, Ties = 70 | Cloud judge did not reproduce the local Agent A bias. |
| `tinyllama:1.1b` lost every decisive cloud row | Reliable weak baseline. |
| `gemma2:2b` vs `llama3.2:3b` was 5-7 with 36 ties | Direct 2B vs 3B comparison remains unresolved. |

### Protocol And Mode Comparison

Folder: `results/2026-08-05_protocol_mode_comparison/`

Evidence quality: paper-grade for completed rows, but same-position `position_a` is partial due to Academic Cloud `429` rate limits.

Key findings:

| Result | Value |
|---|---:|
| Valid judge rows | 80 |
| Skipped/failed rows | 4 |
| Opposing-position rows | 48 |
| Same-position rows | 32 |
| `apertus-70b-instruct-2509` overall wins | 65 / 80 |
| `meta-llama-3.1-8b-instruct` overall wins | 15 / 80 |

Mode-specific interpretation:

| Mode | Result | Interpretation |
|---|---|---|
| Opposing-position paired | Apertus 35 / 48 | Apertus wins, but less overwhelmingly than in same-position. |
| Same-position `position_b` | Apertus 23 / 24 | Same-position strongly favors Apertus when both defend Position B. |
| Same-position `position_a` | Apertus 7 / 8 on `political_ads`; other topics failed with 429 | Partial only; do not use as full position-a same-position result. |

Protocol-specific rankings were stable: Apertus ranked above Meta under all four protocols.

Use in paper: supports that same-position comparison can sharpen candidate differences, but do not claim full rank-correlation/reversal statistics until the partial `position_a` side is rerun after quota recovers.

### Judge Agreement Local Pilot

Folder: `results/2026-08-05_judge_agreement_local_pilot/`

Evidence quality: local diagnostic.

Key findings:

| Result | Value |
|---|---:|
| Planned judge rows | 36 |
| Valid judge rows | 29 |
| Skipped/malformed rows | 7 |
| Agent A wins among valid rows | 26 / 29 |
| Longer response won | 19 / 29 |

Interpretation: this shows local judge reliability problems and strong label bias. It should be used as evidence that judge choice matters and local judges can fail structurally, not as clean judge-agreement evidence.

### Repeated Judgment Local Pilot

Folder: `results/2026-08-05_repeated_judgment_local_pilot/`

Evidence quality: local diagnostic.

Key findings:

| Result | Value |
|---|---:|
| Transcripts | 4 |
| Repeated judge samples per transcript | 3 |
| Valid judge rows | 12 / 12 |
| Within-transcript repeated winner agreement | 4 / 4 groups stable |

Interpretation: `ollama:qwen2.5:3b` was stable in this small repeated sample, but the sample is too small and local-only.

### Style Sensitivity Local Pilot

Folder: `results/2026-08-05_style_sensitivity_local_pilot/`

Evidence quality: local diagnostic / inconclusive.

Key findings:

| Result | Value |
|---|---:|
| Start styles | `neutral`, `assumptions`, `steelman` |
| Valid rows | 12 / 12 |
| Agent A wins | 12 / 12 |

Interpretation: the local judge's Agent A preference overwhelms any detectable style effect. This run is useful as a warning, not as evidence of style robustness.

### Position And Speaking-Order Bias Cloud Run

Folder: `results/2026-08-05_position_order_bias_cloud/`

Evidence quality: paper-grade diagnostic.

Key findings:

| Result | Value |
|---|---:|
| Valid rows | 48 / 48 |
| Position A wins | 15 / 48 |
| Position B wins | 33 / 48 |
| `a_first`: Agent A wins / Agent B wins | 2 / 22 |
| `b_first`: Agent A wins / Agent B wins | 13 / 11 |
| Longer response won | 21 / 48 |

Interpretation: in this cloud run, Position B had a strong advantage and `a_first` heavily favored Agent B. This suggests side/order effects remain important even when parsing is reliable.

### Verbosity Token-Limit Pilot

Folder: `results/2026-08-05_verbosity_length_local_pilot/`

Evidence quality: local diagnostic.

Key findings:

| Result | Value |
|---|---:|
| Valid rows | 16 / 16 |
| Short-token run rows | 8 |
| Long-token run rows | 8 |
| Longer response won | 7 / 16 |
| Average winner length | 156.81 words |
| Average loser length | 155.88 words |

Interpretation: this local token-limit pilot does not show strong verbosity preference. It does not replace a true shortened-same-argument experiment.

### Ideological And Self-Preference Local Pilot

Folder: `results/2026-08-05_ideology_self_preference_local_pilot/`

Evidence quality: local diagnostic / not conclusive.

Key findings:

| Result | Value |
|---|---:|
| Topics | 4 ideological topics |
| Judges | `qwen2.5:3b`, `gemma2:2b` |
| Valid rows | 32 / 32 |
| Agent A wins | 32 / 32 |
| Position B wins | 0 / 32 |

Interpretation: the run is dominated by label/position bias, so it cannot support a real ideological-preference or self-preference claim. It supports the negative methodological claim that local judges can be unusable for ideological-bias inference.

### Position Difficulty Cloud Diagnostic

Folder: `results/2026-08-05_position_difficulty_cloud/`

Evidence quality: paper-grade diagnostic, not a full adjusted regression.

Key findings from the controlled cloud paired run:

| Topic | Position A Wins | Position B Wins | Interpretation |
|---|---:|---:|---|
| `political_ads` | 4 | 12 | Strong Position B advantage in this run. |
| `de_extinction_ethics` | 5 | 11 | Position B advantage. |
| `energy_transition_infrastructure` | 6 | 10 | Position B advantage, with evidence protocol less aligned. |

Protocol-specific note: all protocols favored Position B for `political_ads`; `energy_transition_infrastructure` evidence/fact-checking favored Position A 3-1 while the other protocols favored Position B 3-1.

Use in paper: position difficulty is real enough to motivate controls and per-topic reporting. Do not claim final adjusted causal estimates or uncertainty intervals yet.

## Main Paper Claims Currently Supported

| Claim | Support Level | Evidence |
|---|---|---|
| Stronger/cloud judges improve parseability over small local judges. | Strong | Cloud baseline `144/144` valid vs local baseline `126/144` and local multi-judge `29/36`. |
| Benchmark results are sensitive to role/position/speaker controls. | Strong diagnostic | Cloud position/order run: Position B 33/48, `a_first` Agent B 22/24. |
| Same-position Mode 2 works after prompt fix and can produce sharper candidate separation. | Partial strong | Mode 2 pilot and protocol comparison. |
| Evaluation protocols can change fine-grained results even if top ranking is stable. | Moderate | Some protocol-specific differences, especially energy evidence rows. |
| Local judges can be dominated by label bias. | Strong diagnostic | Style and ideology pilots: Agent A 12/12 and 32/32. |
| TinyLlama is a weak baseline under cloud judging. | Strong | TinyLlama 0 decisive wins in cloud baseline. |

## Claims Not Yet Fully Supported

| Claim | Why Not Yet |
|---|---|
| Final judge-agreement statistics across strong judges | Cloud quota blocked; local judges showed parse/label artifacts. |
| Full repeated-judgment stability | Only one local judge, one topic, four transcripts. |
| True style robustness to rewritten text | Current run changes moderator framing, not post-hoc rewritten transcript style. |
| Causal verbosity bias | Token-limit pilot is not equivalent to shortening the same argument. |
| Ideological judge preference | Local ideological run collapsed into Agent A label bias. |
| Self-preference bias | Local self-judge run is confounded by label bias. |
| Fully adjusted position difficulty with uncertainty intervals | Current result is design-controlled descriptive analysis, not regression/bootstrap inference. |

## Recommended Paper Framing

1. Present the benchmark infrastructure and controls.
2. Present baseline validation: local judge artifacts, then cloud judge improvement.
3. Present protocol/mode comparison as the central experiment, with the caveat that same-position `position_a` was partial due to rate limits.
4. Present bias diagnostics as methodological findings rather than nuisance details.
5. Treat local pilots as stress tests showing where naive evaluation breaks.
6. State explicitly that ideological/self-preference and strong judge-agreement require follow-up cloud runs.

## Follow-Up Runs To Finish Later

When Academic Cloud quota recovers, rerun:

```powershell
python run_benchmark.py --topic-ids political_ads,de_extinction_ethics,energy_transition_infrastructure --benchmark-mode same_position --same-position-target position_a --model-a openai:qwen3-30b-a3b-instruct-2507 --models openai:apertus-70b-instruct-2509,openai:meta-llama-3.1-8b-instruct --judge-model openai:gemma-4-31b-it --judge-mode winner_only --evaluation-protocol all --speaker-order balanced --turns 2 --max-tokens 120 --dry-run
```

And a clean cloud judge-agreement run:

```powershell
python run_benchmark.py --topic-ids political_ads,de_extinction_ethics,energy_transition_infrastructure --benchmark-mode paired --model-a openai:apertus-70b-instruct-2509 --model-b openai:meta-llama-3.1-8b-instruct --judge-models openai:gemma-4-31b-it,openai:qwen3-30b-a3b-instruct-2507 --judge-mode winner_only --evaluation-protocol holistic_persuasion --speaker-order balanced --turns 2 --max-tokens 120 --dry-run
```
