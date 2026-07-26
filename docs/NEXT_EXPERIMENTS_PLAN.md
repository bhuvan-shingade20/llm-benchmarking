# Next Experiments Plan

This plan excludes the earlier AI-assignment topic and focuses on experiments that can support a research paper: robust rankings, methodology sensitivity, judge reliability, bias diagnostics, and topic-level insights. It is aligned with the mentor's proposed Experiment 1-3 structure; see `docs/MENTOR_EXPERIMENT_ALIGNMENT.md` for the detailed gap analysis.

## Mentor-Aligned Priority

| Priority | Mentor Experiment | Status Now | Next Action |
|---:|---|---|---|
| 1 | Evaluation protocol comparison | Partial | Run matched opposing-position and same-position experiments on the same non-AI topic/model set. |
| 2 | Judge agreement | Not cleanly done | Judge a fixed transcript set with multiple judges and compute agreement/rank correlation. |
| 3 | Repeated judgment stability | Not done | Add or run a rejudge-only workflow for repeated judging of saved transcripts. |
| 4 | Position and speaking-order bias | Partial | Compute reversal flip rates and rerun with a stronger cloud judge. |
| 5 | Verbosity bias | Diagnostic only | Run matched-length or shortened-argument conditions. |
| 6 | Ideological preference | Not done | Use a political/ideological topic panel with role swaps and multiple judges. |
| 7 | Position difficulty | Partial | Estimate adjusted position effects with uncertainty intervals. |

## Current Evidence Caveat

The latest baseline ladder is useful as a pilot and sanity check, but not as a final leaderboard. The validity audit in `results/2026-07-25_baseline_capacity_ladder/validity_audit.md` found local judge option-list copying, strong Agent A/Position A effects, topic-side effects, prompt-following failures by small debaters, and verbosity bias. Future paper results should therefore prioritize stronger judges, fixed-transcript rejudging, and explicit bias controls.

## Core Topic Set

Use a stable hard-topic panel for future paper experiments:

| Topic ID | Why It Is Useful |
|---|---|
| `political_ads` | Tests free speech, misinformation, institutional trust, and platform governance. |
| `de_extinction_ethics` | Tests scientific uncertainty, ecological risk, welfare trade-offs, and long-termism. |
| `energy_transition_infrastructure` | Tests technical policy trade-offs, infrastructure constraints, and risk framing. |
| `criminal_justice_framework` | Tests moral reasoning, deterrence, rehabilitation, and institutional design. |
| `cultural_repatriation` | Tests historical justice, preservation risk, identity, and public access. |
| `economic_safety_net` | Tests automation policy, dignity of work, welfare design, and redistribution. |

## Experiment 1: Baseline Capacity Ladder

Status: started in `results/2026-07-25_baseline_capacity_ladder/`.

Purpose: show whether the benchmark can distinguish very small baseline models before comparing stronger cloud models.

Model ladder:

| Tier | Model |
|---|---|
| Sub-1B baseline | `ollama:qwen2.5:0.5b` |
| 1B baseline | `ollama:tinyllama:1.1b` |
| 2B baseline | `ollama:gemma2:2b` |
| 3B baseline | `ollama:llama3.2:3b` |
| 3B judge/control | `ollama:qwen2.5:3b` |

Research value: provides a sanity check, a weak baseline, and a readable contrast between shallow and more coherent argumentation.

## Experiment 2: Cloud-Judged Baseline Validation

Purpose: check whether the local baseline ordering survives when judged by a stronger model.

Recommended judge: `openai:gemma-4-31b-it`.

Design: rerun the baseline capacity ladder on the same three or six hard topics, keeping each adjacent pair separate.

Primary question: do `gemma2:2b` and `qwen2.5:0.5b` still look strong when a stronger judge evaluates them?

## Experiment 3: Strong Model Tournament

Purpose: produce the main paper leaderboard using models that are plausible competitors.

Suggested model pool:

| Provider | Models |
|---|---|
| Academic Cloud | `qwen3-30b-a3b-instruct-2507`, `glm-4.7`, `meta-llama-3.1-8b-instruct` |
| Local reference | `ollama:gemma2:2b`, `ollama:qwen2.5:3b` |

Design: use `--benchmark-mode permutations`, `--speaker-order balanced`, `--evaluation-protocol all`, and one reliable cloud judge first.

Research value: shows whether cloud models separate clearly from small local baselines and whether GLM's earlier advantage over Qwen generalizes beyond one topic.

## Experiment 4: Same-Position Candidate Comparison

Purpose: directly answer the mentor's Mode 2 design.

Design: fix one opponent and compare candidates arguing the same target position across separate debates.

Run both target sides:

| Variant | Setting |
|---|---|
| Candidate defends Position A | `--same-position-target position_a` |
| Candidate defends Position B | `--same-position-target position_b` |

Research value: separates candidate skill from topic-side assignment and gives a more interactive paper story than only direct head-to-head debates.

## Experiment 5: Judge Robustness And Agreement

Purpose: measure whether rankings depend on the judge.

Design: rerun a fixed set of transcripts with multiple judges.

Suggested judges:

| Judge | Role |
|---|---|
| `openai:gemma-4-31b-it` | Preferred reliable cloud judge. |
| `openai:qwen3-30b-a3b-instruct-2507` | Strong alternate judge if parseable. |
| `ollama:qwen2.5:3b` | Cheap local judge for comparison. |

Metrics to report: judge agreement, model rank changes by judge, invalid JSON rate, confidence distributions, and systematic label bias.

## Experiment 6: Protocol Sensitivity Study

Purpose: test whether `holistic_persuasion`, `argument_quality`, `evidence_fact_check`, and `deliberative_quality` produce the same winners.

Design: judge each transcript under all four protocols and visualize rank movement with the bump chart.

Research value: turns the evaluation protocol itself into a contribution, showing that model rankings are method-sensitive.

## Experiment 7: Bias Stress Test

Purpose: quantify artifacts that can distort conclusions.

Design: use the same model pair and topic under controlled variations.

Controls:

| Bias Check | Manipulation |
|---|---|
| Position-label bias | Swap Position A and Position B assignments. |
| Speaker-order bias | Use `--speaker-order balanced`. |
| Judge self-preference | Avoid using a judge that is also a debater; compare against a self-judge condition only as a diagnostic. |
| Verbosity bias | Compare fixed token limits and report winner/loser word counts. |
| Topic-side bias | Report wins by topic and by defended position, not only by model. |

Research value: makes the paper stronger because it does not just present a leaderboard; it explains when leaderboards become unreliable.

## Experiment 8: Topic Difficulty And Polarization Map

Purpose: identify which topics are easy, ambiguous, or side-biased.

Metrics:

| Metric | Meaning |
|---|---|
| Decisive win rate | Whether judges consistently choose a winner. |
| Average confidence | Whether the judge sees clear quality differences. |
| Position A/B win split | Whether the topic framing favors one side. |
| Protocol disagreement | Whether different rubrics disagree on the same transcript. |
| Judge disagreement | Whether judges rank the same transcript differently. |

Research value: lets the paper include a topic map or heatmap, making the benchmark more interactive and interpretable.

## Recommended Paper Story

1. Start with simple baselines to show the benchmark behaves sensibly but is not free of artifacts.
2. Show that direct debate rankings change with topic, position, protocol, and judge.
3. Introduce same-position comparison as a cleaner alternative for candidate comparison.
4. Use cloud-judged strong-model tournaments for the main leaderboard.
5. Use bias diagnostics and protocol bump charts as the methodological contribution.

## Storage Rule

Every new experiment should be saved in a dated descriptive folder:

```powershell
results/YYYY-MM-DD_experiment_name/
```

After each run, copy the CSV/JSON outputs into that folder and generate folder-specific reports:

```powershell
python analyze_all_results.py --input-glob "results/YYYY-MM-DD_experiment_name/*_results.csv" --output-dir "results/YYYY-MM-DD_experiment_name" --output-prefix "experiment_name"
```
