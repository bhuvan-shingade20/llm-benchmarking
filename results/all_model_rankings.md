# Model Ranking Summary (All Runs)

Generated from 154 valid judge evaluations across 38 benchmark result files.
Skipped 30 rows with judge parse errors, run errors, or missing model fields.
Headline ranking requires at least 5 valid debates per model to avoid tiny-sample leaders.
Evaluation protocol bump chart: `results\evaluation_protocol_bump_chart.svg`.

## Mentor Summary

| Point | Current Status |
|-------|----------------|
| Four evaluation protocols | Implemented: holistic persuasion, argument quality, evidence/fact-checking, and deliberative quality. Use `--evaluation-protocol all` to judge the same transcript under all four. |
| Protocol comparison graph | Implemented as a bump chart in `results/evaluation_protocol_bump_chart.svg`; x-axis is evaluation protocol, y-axis is model rank. |
| Better model ranking | Headline ranking now filters out models with fewer than 5 valid debates; low-sample models are listed separately as preliminary. |
| Judging bias checks | Report now includes position/order bias and a length-bias diagnostic based on transcript word counts. |
| Balanced position/order control | `--speaker-order balanced` remains the default for benchmark runs. |
| Provider diversity | Academic Cloud and Ollama rows are both included; legacy unprefixed rows are labeled as `academic_cloud`. |

## Evaluation Protocols

| Protocol | What It Measures |
|----------|------------------|
| `holistic_persuasion` | Overall neutral-reader persuasiveness. |
| `argument_quality` | Claim-warrant structure, burden of proof, coherence, and rebuttal strength. |
| `evidence_fact_check` | Factfulness, groundedness, and unsupported-claim penalties. |
| `deliberative_quality` | Responsiveness, fair engagement, steelmanning, and intellectual honesty. |

## Qualified Model Ranking

Models below 5 valid debates are excluded from this headline table.

| Rank | Model | Provider | Debates | Wins | Losses | Ties | Win Rate | Avg Overall | Avg Factfulness | Avg Groundedness | Avg Confidence |
|------|-------|----------|---------|------|--------|------|----------|-------------|-----------------|------------------|----------------|
| 1 | glm-4.7 | academic_cloud | 18 | 15 | 3 | 0 | 0.83 | N/A | N/A | N/A | 0.81 |
| 2 | qwen3-30b-a3b-instruct-2507 | academic_cloud | 114 | 83 | 28 | 3 | 0.73 | 7.50 | 8.50 | 9.14 | 0.83 |
| 3 | mistral-large-3-675b-instruct-2512 | academic_cloud | 16 | 8 | 8 | 0 | 0.50 | 7.64 | 8.57 | 9.21 | 0.82 |
| 4 | qwen2.5:3b | ollama | 6 | 3 | 2 | 1 | 0.50 | N/A | N/A | N/A | 0.82 |
| 5 | meta-llama-3.1-8b-instruct | academic_cloud | 50 | 14 | 32 | 4 | 0.28 | N/A | N/A | N/A | 0.83 |
| 6 | apertus-70b-instruct-2509 | academic_cloud | 89 | 21 | 63 | 5 | 0.24 | 8.00 | 9.00 | 9.00 | 0.83 |
| 7 | llama3.2:3b | ollama | 9 | 0 | 8 | 1 | 0.00 | 3.00 | 8.00 | 9.00 | 0.88 |

## Preliminary Low-Sample Models

These models have promising or poor win rates, but too few debates for a fair leaderboard position.

| Rank | Model | Provider | Debates | Wins | Losses | Ties | Win Rate | Avg Overall | Avg Factfulness | Avg Groundedness | Avg Confidence |
|------|-------|----------|---------|------|--------|------|----------|-------------|-----------------|------------------|----------------|
| 1 | gemma-4-31b-it | academic_cloud | 4 | 3 | 1 | 0 | 0.75 | N/A | N/A | N/A | 0.95 |
| 2 | devstral-2-123b-instruct-2512 | academic_cloud | 2 | 0 | 2 | 0 | 0.00 | N/A | N/A | N/A | 0.80 |

## Complete Exploratory Ranking

This includes every valid row and is useful for debugging, but should not be presented as the final fair leaderboard.

| Rank | Model | Provider | Debates | Wins | Losses | Ties | Win Rate | Avg Overall | Avg Factfulness | Avg Groundedness | Avg Confidence | Status |
|------|-------|----------|---------|------|--------|------|----------|-------------|-----------------|------------------|----------------|--------|
| 1 | glm-4.7 | academic_cloud | 18 | 15 | 3 | 0 | 0.83 | N/A | N/A | N/A | 0.81 | qualified |
| 2 | gemma-4-31b-it | academic_cloud | 4 | 3 | 1 | 0 | 0.75 | N/A | N/A | N/A | 0.95 | preliminary |
| 3 | qwen3-30b-a3b-instruct-2507 | academic_cloud | 114 | 83 | 28 | 3 | 0.73 | 7.50 | 8.50 | 9.14 | 0.83 | qualified |
| 4 | mistral-large-3-675b-instruct-2512 | academic_cloud | 16 | 8 | 8 | 0 | 0.50 | 7.64 | 8.57 | 9.21 | 0.82 | qualified |
| 5 | qwen2.5:3b | ollama | 6 | 3 | 2 | 1 | 0.50 | N/A | N/A | N/A | 0.82 | qualified |
| 6 | meta-llama-3.1-8b-instruct | academic_cloud | 50 | 14 | 32 | 4 | 0.28 | N/A | N/A | N/A | 0.83 | qualified |
| 7 | apertus-70b-instruct-2509 | academic_cloud | 89 | 21 | 63 | 5 | 0.24 | 8.00 | 9.00 | 9.00 | 0.83 | qualified |
| 8 | devstral-2-123b-instruct-2512 | academic_cloud | 2 | 0 | 2 | 0 | 0.00 | N/A | N/A | N/A | 0.80 | preliminary |
| 9 | llama3.2:3b | ollama | 9 | 0 | 8 | 1 | 0.00 | 3.00 | 8.00 | 9.00 | 0.88 | qualified |

## Balanced-Only Ranking

Only rows with explicit `speaker_order` equal to `a_first` or `b_first` are included here; legacy one-order rows are excluded.

| Rank | Model | Provider | Debates | Wins | Losses | Ties | Win Rate | Avg Overall | Avg Factfulness | Avg Groundedness | Avg Confidence | Status |
|------|-------|----------|---------|------|--------|------|----------|-------------|-----------------|------------------|----------------|--------|
| 1 | glm-4.7 | academic_cloud | 18 | 15 | 3 | 0 | 0.83 | N/A | N/A | N/A | 0.81 | qualified |
| 2 | qwen3-30b-a3b-instruct-2507 | academic_cloud | 96 | 72 | 21 | 3 | 0.75 | N/A | N/A | N/A | 0.83 | qualified |
| 3 | gemma-4-31b-it | academic_cloud | 4 | 3 | 1 | 0 | 0.75 | N/A | N/A | N/A | 0.95 | preliminary |
| 4 | qwen2.5:3b | ollama | 6 | 3 | 2 | 1 | 0.50 | N/A | N/A | N/A | 0.82 | qualified |
| 5 | meta-llama-3.1-8b-instruct | academic_cloud | 50 | 14 | 32 | 4 | 0.28 | N/A | N/A | N/A | 0.83 | qualified |
| 6 | apertus-70b-instruct-2509 | academic_cloud | 89 | 21 | 63 | 5 | 0.24 | 8.00 | 9.00 | 9.00 | 0.83 | qualified |
| 7 | devstral-2-123b-instruct-2512 | academic_cloud | 2 | 0 | 2 | 0 | 0.00 | N/A | N/A | N/A | 0.80 | preliminary |
| 8 | llama3.2:3b | ollama | 5 | 0 | 4 | 1 | 0.00 | 3.00 | 8.00 | 9.00 | 0.86 | qualified |

## Per-Provider Summary

| Provider | Total Debates | Wins | Losses | Ties | Win Rate |
|----------|---------------|------|--------|------|----------|
| academic_cloud | 293 | 144 | 137 | 12 | 0.49 |
| ollama | 15 | 3 | 10 | 2 | 0.20 |

## Benchmark Mode Coverage

| Benchmark Mode | Debates | Agent A Wins | Agent B Wins | Ties |
|---|---:|---:|---:|---:|
| Legacy | 13 | 1 | 12 | 0 |
| paired | 14 | 6 | 8 | 0 |
| permutations | 58 | 23 | 34 | 1 |
| single | 69 | 23 | 40 | 6 |

## Judge Mode Coverage

| Judge Mode | Debates | Agent A Wins | Agent B Wins | Ties |
|---|---:|---:|---:|---:|
| detailed | 2 | 0 | 2 | 0 |
| Legacy | 13 | 1 | 12 | 0 |
| winner_only | 139 | 52 | 80 | 7 |

## Evaluation Protocol Coverage

| Evaluation Protocol | Debates | Agent A Wins | Agent B Wins | Ties |
|---|---:|---:|---:|---:|
| Argument | 30 | 13 | 17 | 0 |
| Deliberative | 28 | 14 | 14 | 0 |
| Evidence | 29 | 7 | 17 | 5 |
| Holistic | 29 | 11 | 17 | 1 |
| Legacy | 38 | 8 | 29 | 1 |

## Protocol-Specific Rankings

### Holistic

| Rank | Model | Provider | Debates | Wins | Losses | Ties | Win Rate | Avg Overall | Avg Factfulness | Avg Groundedness | Avg Confidence | Status |
|------|-------|----------|---------|------|--------|------|----------|-------------|-----------------|------------------|----------------|--------|
| 1 | qwen3-30b-a3b-instruct-2507 | academic_cloud | 24 | 18 | 6 | 0 | 0.75 | N/A | N/A | N/A | 0.82 | qualified |
| 2 | glm-4.7 | academic_cloud | 4 | 3 | 1 | 0 | 0.75 | N/A | N/A | N/A | 0.80 | preliminary |
| 3 | apertus-70b-instruct-2509 | academic_cloud | 19 | 5 | 13 | 1 | 0.26 | N/A | N/A | N/A | 0.82 | qualified |
| 4 | meta-llama-3.1-8b-instruct | academic_cloud | 11 | 2 | 8 | 1 | 0.18 | N/A | N/A | N/A | 0.81 | qualified |

### Argument

| Rank | Model | Provider | Debates | Wins | Losses | Ties | Win Rate | Avg Overall | Avg Factfulness | Avg Groundedness | Avg Confidence | Status |
|------|-------|----------|---------|------|--------|------|----------|-------------|-----------------|------------------|----------------|--------|
| 1 | qwen3-30b-a3b-instruct-2507 | academic_cloud | 25 | 20 | 5 | 0 | 0.80 | N/A | N/A | N/A | 0.84 | qualified |
| 2 | glm-4.7 | academic_cloud | 4 | 3 | 1 | 0 | 0.75 | N/A | N/A | N/A | 0.85 | preliminary |
| 3 | meta-llama-3.1-8b-instruct | academic_cloud | 11 | 3 | 8 | 0 | 0.27 | N/A | N/A | N/A | 0.82 | qualified |
| 4 | apertus-70b-instruct-2509 | academic_cloud | 20 | 4 | 16 | 0 | 0.20 | N/A | N/A | N/A | 0.83 | qualified |

### Evidence

| Rank | Model | Provider | Debates | Wins | Losses | Ties | Win Rate | Avg Overall | Avg Factfulness | Avg Groundedness | Avg Confidence | Status |
|------|-------|----------|---------|------|--------|------|----------|-------------|-----------------|------------------|----------------|--------|
| 1 | glm-4.7 | academic_cloud | 4 | 4 | 0 | 0 | 1.00 | N/A | N/A | N/A | 0.80 | preliminary |
| 2 | qwen3-30b-a3b-instruct-2507 | academic_cloud | 24 | 16 | 5 | 3 | 0.67 | N/A | N/A | N/A | 0.83 | qualified |
| 3 | meta-llama-3.1-8b-instruct | academic_cloud | 10 | 2 | 5 | 3 | 0.20 | N/A | N/A | N/A | 0.88 | qualified |
| 4 | apertus-70b-instruct-2509 | academic_cloud | 20 | 2 | 14 | 4 | 0.10 | N/A | N/A | N/A | 0.84 | qualified |

### Deliberative

| Rank | Model | Provider | Debates | Wins | Losses | Ties | Win Rate | Avg Overall | Avg Factfulness | Avg Groundedness | Avg Confidence | Status |
|------|-------|----------|---------|------|--------|------|----------|-------------|-----------------|------------------|----------------|--------|
| 1 | qwen3-30b-a3b-instruct-2507 | academic_cloud | 23 | 18 | 5 | 0 | 0.78 | N/A | N/A | N/A | 0.83 | qualified |
| 2 | glm-4.7 | academic_cloud | 4 | 3 | 1 | 0 | 0.75 | N/A | N/A | N/A | 0.81 | preliminary |
| 3 | meta-llama-3.1-8b-instruct | academic_cloud | 10 | 3 | 7 | 0 | 0.30 | N/A | N/A | N/A | 0.81 | qualified |
| 4 | apertus-70b-instruct-2509 | academic_cloud | 19 | 4 | 15 | 0 | 0.21 | N/A | N/A | N/A | 0.82 | qualified |


## Position Win Rates

| Position | Debates | Wins | Win Rate |
|----------|---------|------|----------|
| Position A | 154 | 53 | 0.34 |
| Position B | 154 | 94 | 0.61 |

## Speaker Order Effects

| Speaker Order | Debates | Agent A Wins | Agent B Wins | Ties |
|---|---:|---:|---:|---:|
| a_first | 75 | 21 | 47 | 7 |
| a_first (legacy) | 19 | 2 | 17 | 0 |
| b_first | 60 | 30 | 30 | 0 |

## Judging Bias Diagnostics

| Bias Check | Result | Interpretation |
|------------|--------|----------------|
| Length bias | Longer agent won 72 / 154 comparable rows (0.47) | Values well above 0.50 suggest judges may reward verbosity. |
| Average winner length | 161.64 words | Compare with loser length below. |
| Average loser length | 161.56 words | If winners are much longer, inspect for verbosity bias. |
| Average Agent A length | 160.12 words | Helps detect role/order verbosity differences. |
| Average Agent B length | 162.73 words | Helps detect role/order verbosity differences. |
| Position/order bias | See `Position Win Rates` and `Speaker Order Effects` above | Legacy rows should not drive final conclusions. |

## Per-Topic Summary

| Topic | Debates | Decisive Wins |
|-------|---------|---------------|
| ai_assignments | 125 | 118 |
| assessment_design | 5 | 5 |
| cultural_repatriation | 4 | 4 |
| public_software | 5 | 5 |
| remote_work | 7 | 7 |
| right_to_be_forgotten | 4 | 4 |
| urban_density_zoning | 4 | 4 |

## Recommended Fair Rerun Plan

Use a fixed model pool and enough topics so every model gets at least 5-6 valid debates under balanced order. Example:

```powershell
python run_benchmark.py --topic-ids ai_assignments,remote_work,assessment_design --benchmark-mode permutations --models openai:qwen3-30b-a3b-instruct-2507,openai:mistral-large-3-675b-instruct-2512,openai:apertus-70b-instruct-2509,ollama:qwen2.5:3b --judge-model openai:gemma-4-31b-it --judge-mode winner_only --evaluation-protocol all --speaker-order balanced --turns 2 --max-tokens 120 --dry-run
```

Remove `--dry-run` only after checking the planned judge-evaluation count, because protocols multiply judge calls by four.

## Questions For Mentor

1. Should the final leaderboard include only qualified models with at least 5-6 valid debates?
2. Should the paper report the four protocol rankings separately or average them into one meta-ranking?
3. Is the bump chart the right visualization for protocol sensitivity, or should we also add bar charts of win rate by protocol?
4. Should length bias be corrected statistically, or only reported as a diagnostic?
5. Should Academic Cloud and Ollama/local models be separate leaderboards because model size differs greatly?

## Recent Benchmark Runs

| Run ID | Valid Evaluations | Topics | Models | Benchmark Modes | Judge Modes | Protocols |
|--------|-------------------|--------|--------|-----------------|-------------|-----------|
| 20260722_132539_675669_25364_benchmark | 4 | ai_assignments | academic_cloud:apertus-70b-instruct-2509, academic_cloud:qwen3-30b-a3b-instruct-2507 | single | winner_only | Argument, Deliberative, Evidence, Holistic |
| 20260722_132602_088278_17268_benchmark | 4 | ai_assignments | academic_cloud:apertus-70b-instruct-2509, academic_cloud:meta-llama-3.1-8b-instruct | single | winner_only | Argument, Deliberative, Evidence, Holistic |
| 20260722_132622_407833_34316_benchmark | 4 | ai_assignments | academic_cloud:meta-llama-3.1-8b-instruct, academic_cloud:qwen3-30b-a3b-instruct-2507 | single | winner_only | Argument, Deliberative, Evidence, Holistic |
| 20260722_132651_338874_5984_benchmark | 4 | ai_assignments | academic_cloud:apertus-70b-instruct-2509, academic_cloud:qwen3-30b-a3b-instruct-2507 | single | winner_only | Argument, Deliberative, Evidence, Holistic |
| 20260722_134047_384650_30328_benchmark | 13 | ai_assignments | academic_cloud:glm-4.7, academic_cloud:qwen3-30b-a3b-instruct-2507 | permutations | winner_only | Argument, Deliberative, Evidence, Holistic |
| 20260722_134456_583102_20384_benchmark | 1 | ai_assignments | academic_cloud:glm-4.7, academic_cloud:qwen3-30b-a3b-instruct-2507 | single | winner_only | Evidence |
| 20260722_134521_548713_11400_benchmark | 1 | ai_assignments | academic_cloud:glm-4.7, academic_cloud:qwen3-30b-a3b-instruct-2507 | single | winner_only | Evidence |
| 20260722_134610_864163_36488_benchmark | 1 | ai_assignments | academic_cloud:glm-4.7, academic_cloud:qwen3-30b-a3b-instruct-2507 | single | winner_only | Argument |

## Reliability Notes

| Issue | Count / Evidence | Handling |
|-------|------------------|----------|
| Invalid or failed rows | 30 rows skipped | Kept in raw CSV/JSON but excluded from win/loss rankings. |
| Malformed detailed judge JSON | Observed in a `judge-mode both` run | Winner-only result remains usable; detailed row is skipped in all-runs ranking. |
| Slow or unstable endpoints | Some Academic Cloud endpoints returned empty/500 responses or timed out | Treat endpoint reliability as a separate experimental observation. |
| Legacy position-order bias | Older rows lack `speaker_order` and default to `a_first (legacy)` | Use balanced speaker-order runs for future conclusions. |

## Individual Valid Debates

| Run ID | Topic | Protocol | Speaker Order | Position A Model | Position B Model | Winner | Confidence |
|--------|-------|----------|---------------|------------------|------------------|--------|------------|
| 20260616_190909_benchmark | ai_assignments | Legacy | a_first (legacy) | academic_cloud:mistral-large-3-675b-instruct-2512 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.85 |
| 20260616_200632_benchmark | cultural_repatriation | Legacy | a_first (legacy) | academic_cloud:mistral-large-3-675b-instruct-2512 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260616_200632_benchmark | cultural_repatriation | Legacy | a_first (legacy) | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:mistral-large-3-675b-instruct-2512 | Agent B | 0.8 |
| 20260616_200632_benchmark | cultural_repatriation | Legacy | a_first (legacy) | academic_cloud:mistral-large-3-675b-instruct-2512 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260616_200632_benchmark | cultural_repatriation | Legacy | a_first (legacy) | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:mistral-large-3-675b-instruct-2512 | Agent B | 0.9 |
| 20260616_200632_benchmark | right_to_be_forgotten | Legacy | a_first (legacy) | academic_cloud:mistral-large-3-675b-instruct-2512 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260616_200632_benchmark | right_to_be_forgotten | Legacy | a_first (legacy) | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:mistral-large-3-675b-instruct-2512 | Agent B | 0.8 |
| 20260616_200632_benchmark | right_to_be_forgotten | Legacy | a_first (legacy) | academic_cloud:mistral-large-3-675b-instruct-2512 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent A | 0.8 |
| 20260616_200632_benchmark | right_to_be_forgotten | Legacy | a_first (legacy) | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:mistral-large-3-675b-instruct-2512 | Agent B | 0.8 |
| 20260616_200632_benchmark | urban_density_zoning | Legacy | a_first (legacy) | academic_cloud:mistral-large-3-675b-instruct-2512 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260616_200632_benchmark | urban_density_zoning | Legacy | a_first (legacy) | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:mistral-large-3-675b-instruct-2512 | Agent B | 0.8 |
| 20260616_200632_benchmark | urban_density_zoning | Legacy | a_first (legacy) | academic_cloud:mistral-large-3-675b-instruct-2512 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260616_200632_benchmark | urban_density_zoning | Legacy | a_first (legacy) | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:mistral-large-3-675b-instruct-2512 | Agent B | 0.8 |
| 20260627_025752_benchmark | ai_assignments | Legacy | a_first (legacy) | ollama:llama3.2:3b | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.9 |
| 20260627_034300_benchmark | ai_assignments | Legacy | a_first (legacy) | ollama:llama3.2:3b | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.9 |
| 20260627_034339_benchmark | remote_work | Legacy | a_first (legacy) | academic_cloud:qwen3-30b-a3b-instruct-2507 | ollama:llama3.2:3b | Agent A | 0.8 |
| 20260627_034418_benchmark | assessment_design | Legacy | a_first (legacy) | ollama:llama3.2:3b | academic_cloud:mistral-large-3-675b-instruct-2512 | Agent B | 1.0 |
| 20260627_035412_benchmark | public_software | Legacy | a_first (legacy) | academic_cloud:mistral-large-3-675b-instruct-2512 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260627_035412_benchmark | public_software | Legacy | a_first (legacy) | academic_cloud:mistral-large-3-675b-instruct-2512 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260710_130658_benchmark | ai_assignments | Legacy | a_first | academic_cloud:meta-llama-3.1-8b-instruct | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.8 |
| 20260710_130658_benchmark | ai_assignments | Legacy | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:meta-llama-3.1-8b-instruct | Agent B | 0.8 |
| 20260710_130658_benchmark | ai_assignments | Legacy | b_first | academic_cloud:meta-llama-3.1-8b-instruct | academic_cloud:apertus-70b-instruct-2509 | Agent B | 0.8 |
| 20260710_130658_benchmark | ai_assignments | Legacy | b_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:meta-llama-3.1-8b-instruct | Agent A | 0.8 |
| 20260710_130842_349342_benchmark | remote_work | Legacy | a_first | academic_cloud:gemma-4-31b-it | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.95 |
| 20260710_130842_349342_benchmark | remote_work | Legacy | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:gemma-4-31b-it | Agent B | 0.95 |
| 20260710_130842_349342_benchmark | remote_work | Legacy | b_first | academic_cloud:gemma-4-31b-it | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.95 |
| 20260710_130842_349342_benchmark | remote_work | Legacy | b_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:gemma-4-31b-it | Agent A | 0.95 |
| 20260710_131647_627729_benchmark | assessment_design | Legacy | a_first | ollama:qwen2.5:3b | academic_cloud:meta-llama-3.1-8b-instruct | Agent B | 0.8 |
| 20260710_131647_627729_benchmark | assessment_design | Legacy | a_first | academic_cloud:meta-llama-3.1-8b-instruct | ollama:qwen2.5:3b | Agent B | 0.8 |
| 20260710_131647_627729_benchmark | assessment_design | Legacy | b_first | ollama:qwen2.5:3b | academic_cloud:meta-llama-3.1-8b-instruct | Agent B | 0.8 |
| 20260710_131647_627729_benchmark | assessment_design | Legacy | b_first | academic_cloud:meta-llama-3.1-8b-instruct | ollama:qwen2.5:3b | Agent B | 0.8 |
| 20260710_131947_642743_benchmark | public_software | Legacy | a_first | ollama:llama3.2:3b | academic_cloud:apertus-70b-instruct-2509 | Agent B | 0.8 |
| 20260710_131947_642743_benchmark | public_software | Legacy | b_first | ollama:llama3.2:3b | academic_cloud:apertus-70b-instruct-2509 | Agent B | 0.9 |
| 20260710_131947_642743_benchmark | public_software | Legacy | b_first | ollama:llama3.2:3b | academic_cloud:apertus-70b-instruct-2509 | Agent B | 0.9 |
| 20260710_132158_682763_benchmark | remote_work | Legacy | a_first | academic_cloud:devstral-2-123b-instruct-2512 | academic_cloud:glm-4.7 | Agent B | 0.8 |
| 20260710_132158_682763_benchmark | remote_work | Legacy | a_first | academic_cloud:glm-4.7 | academic_cloud:devstral-2-123b-instruct-2512 | Agent A | 0.8 |
| 20260710_133724_435070_benchmark | ai_assignments | Legacy | a_first | ollama:llama3.2:3b | ollama:qwen2.5:3b | Tie | 0.8 |
| 20260710_133724_435070_benchmark | ai_assignments | Legacy | b_first | ollama:llama3.2:3b | ollama:qwen2.5:3b | Agent B | 0.9 |
| 20260722_122523_620505_7888_benchmark | ai_assignments | Argument | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.8 |
| 20260722_122523_620505_7888_benchmark | ai_assignments | Deliberative | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.8 |
| 20260722_122523_620505_7888_benchmark | ai_assignments | Evidence | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent B | 0.8 |
| 20260722_122523_620505_7888_benchmark | ai_assignments | Holistic | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent B | 0.8 |
| 20260722_122523_620505_7888_benchmark | ai_assignments | Argument | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.9 |
| 20260722_122523_620505_7888_benchmark | ai_assignments | Deliberative | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.9 |
| 20260722_122523_620505_7888_benchmark | ai_assignments | Evidence | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260722_122523_620505_7888_benchmark | ai_assignments | Holistic | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.9 |
| 20260722_122523_620505_7888_benchmark | ai_assignments | Argument | b_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.85 |
| 20260722_122523_620505_7888_benchmark | ai_assignments | Deliberative | b_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.8 |
| 20260722_122523_620505_7888_benchmark | ai_assignments | Evidence | b_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent A |  |
| 20260722_122523_620505_7888_benchmark | ai_assignments | Holistic | b_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.8 |
| 20260722_122523_620505_7888_benchmark | ai_assignments | Argument | b_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent A | 0.8 |
| 20260722_122523_620505_7888_benchmark | ai_assignments | Deliberative | b_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260722_122523_620505_7888_benchmark | ai_assignments | Evidence | b_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260722_122523_620505_7888_benchmark | ai_assignments | Holistic | b_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent A | 0.8 |
| 20260722_124015_599148_24460_benchmark | ai_assignments | Argument | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.9 |
| 20260722_124015_599148_24460_benchmark | ai_assignments | Deliberative | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.85 |
| 20260722_124015_599148_24460_benchmark | ai_assignments | Evidence | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260722_124015_599148_24460_benchmark | ai_assignments | Holistic | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260722_124015_599148_24460_benchmark | ai_assignments | Argument | b_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.85 |
| 20260722_124015_599148_24460_benchmark | ai_assignments | Deliberative | b_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.8 |
| 20260722_124015_599148_24460_benchmark | ai_assignments | Evidence | b_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.8 |
| 20260722_124015_599148_24460_benchmark | ai_assignments | Holistic | b_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.85 |
| 20260722_124015_599148_24460_benchmark | ai_assignments | Argument | b_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260722_124015_599148_24460_benchmark | ai_assignments | Deliberative | b_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent A | 0.8 |
| 20260722_124015_599148_24460_benchmark | ai_assignments | Evidence | b_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260722_124015_599148_24460_benchmark | ai_assignments | Holistic | b_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260722_125125_912640_35340_benchmark | ai_assignments | Argument | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.8 |
| 20260722_125125_912640_35340_benchmark | ai_assignments | Deliberative | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.8 |
| 20260722_125125_912640_35340_benchmark | ai_assignments | Evidence | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Tie | 0.8 |
| 20260722_125125_912640_35340_benchmark | ai_assignments | Holistic | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.8 |
| 20260722_131835_325631_30752_benchmark | ai_assignments | Argument | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.8 |
| 20260722_131835_325631_30752_benchmark | ai_assignments | Deliberative | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.8 |
| 20260722_131835_325631_30752_benchmark | ai_assignments | Evidence | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.8 |
| 20260722_131835_325631_30752_benchmark | ai_assignments | Holistic | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.8 |
| 20260722_131835_325631_30752_benchmark | ai_assignments | Argument | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:meta-llama-3.1-8b-instruct | Agent A | 0.8 |
| 20260722_131835_325631_30752_benchmark | ai_assignments | Holistic | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:meta-llama-3.1-8b-instruct | Agent A | 0.8 |
| 20260722_131835_325631_30752_benchmark | ai_assignments | Argument | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.85 |
| 20260722_131835_325631_30752_benchmark | ai_assignments | Evidence | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260722_131835_325631_30752_benchmark | ai_assignments | Holistic | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260722_131835_325631_30752_benchmark | ai_assignments | Argument | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:meta-llama-3.1-8b-instruct | Agent B | 0.8 |
| 20260722_131835_325631_30752_benchmark | ai_assignments | Deliberative | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:meta-llama-3.1-8b-instruct | Agent A | 0.8 |
| 20260722_131835_325631_30752_benchmark | ai_assignments | Evidence | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:meta-llama-3.1-8b-instruct | Tie | 1.0 |
| 20260722_131835_325631_30752_benchmark | ai_assignments | Holistic | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:meta-llama-3.1-8b-instruct | Agent B | 0.8 |
| 20260722_131835_325631_30752_benchmark | ai_assignments | Argument | a_first | academic_cloud:meta-llama-3.1-8b-instruct | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.9 |
| 20260722_131835_325631_30752_benchmark | ai_assignments | Deliberative | a_first | academic_cloud:meta-llama-3.1-8b-instruct | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260722_131835_325631_30752_benchmark | ai_assignments | Evidence | a_first | academic_cloud:meta-llama-3.1-8b-instruct | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260722_131835_325631_30752_benchmark | ai_assignments | Holistic | a_first | academic_cloud:meta-llama-3.1-8b-instruct | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.85 |
| 20260722_132134_785481_6424_benchmark | ai_assignments | Argument | a_first | academic_cloud:meta-llama-3.1-8b-instruct | academic_cloud:apertus-70b-instruct-2509 | Agent A |  |
| 20260722_132134_785481_6424_benchmark | ai_assignments | Deliberative | a_first | academic_cloud:meta-llama-3.1-8b-instruct | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.8 |
| 20260722_132134_785481_6424_benchmark | ai_assignments | Evidence | a_first | academic_cloud:meta-llama-3.1-8b-instruct | academic_cloud:apertus-70b-instruct-2509 | Tie | 1.0 |
| 20260722_132134_785481_6424_benchmark | ai_assignments | Holistic | a_first | academic_cloud:meta-llama-3.1-8b-instruct | academic_cloud:apertus-70b-instruct-2509 | Tie | 0.8 |
| 20260722_132232_775202_29456_benchmark | ai_assignments | Argument | b_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent A |  |
| 20260722_132232_775202_29456_benchmark | ai_assignments | Deliberative | b_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.8 |
| 20260722_132232_775202_29456_benchmark | ai_assignments | Evidence | b_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.8 |
| 20260722_132232_775202_29456_benchmark | ai_assignments | Holistic | b_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.8 |
| 20260722_132252_759809_5916_benchmark | ai_assignments | Argument | b_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:meta-llama-3.1-8b-instruct | Agent A | 0.85 |
| 20260722_132252_759809_5916_benchmark | ai_assignments | Deliberative | b_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:meta-llama-3.1-8b-instruct | Agent A | 0.8 |
| 20260722_132252_759809_5916_benchmark | ai_assignments | Evidence | b_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:meta-llama-3.1-8b-instruct | Agent A | 0.8 |
| 20260722_132252_759809_5916_benchmark | ai_assignments | Holistic | b_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:meta-llama-3.1-8b-instruct | Agent A | 0.8 |
| 20260722_132311_190801_11396_benchmark | ai_assignments | Argument | b_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260722_132311_190801_11396_benchmark | ai_assignments | Deliberative | b_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260722_132311_190801_11396_benchmark | ai_assignments | Evidence | b_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260722_132338_297089_2424_benchmark | ai_assignments | Argument | b_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:meta-llama-3.1-8b-instruct | Agent A | 0.8 |
| 20260722_132338_297089_2424_benchmark | ai_assignments | Deliberative | b_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:meta-llama-3.1-8b-instruct | Agent A | 0.8 |
| 20260722_132338_297089_2424_benchmark | ai_assignments | Evidence | b_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:meta-llama-3.1-8b-instruct | Agent B | 0.8 |
| 20260722_132338_297089_2424_benchmark | ai_assignments | Holistic | b_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:meta-llama-3.1-8b-instruct | Agent A | 0.8 |
| 20260722_132401_896874_36552_benchmark | ai_assignments | Argument | b_first | academic_cloud:meta-llama-3.1-8b-instruct | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260722_132401_896874_36552_benchmark | ai_assignments | Deliberative | b_first | academic_cloud:meta-llama-3.1-8b-instruct | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260722_132401_896874_36552_benchmark | ai_assignments | Evidence | b_first | academic_cloud:meta-llama-3.1-8b-instruct | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260722_132401_896874_36552_benchmark | ai_assignments | Holistic | b_first | academic_cloud:meta-llama-3.1-8b-instruct | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260722_132417_661111_29140_benchmark | ai_assignments | Argument | b_first | academic_cloud:meta-llama-3.1-8b-instruct | academic_cloud:apertus-70b-instruct-2509 | Agent B | 0.8 |
| 20260722_132417_661111_29140_benchmark | ai_assignments | Deliberative | b_first | academic_cloud:meta-llama-3.1-8b-instruct | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.8 |
| 20260722_132417_661111_29140_benchmark | ai_assignments | Evidence | b_first | academic_cloud:meta-llama-3.1-8b-instruct | academic_cloud:apertus-70b-instruct-2509 | Agent B | 0.8 |
| 20260722_132417_661111_29140_benchmark | ai_assignments | Holistic | b_first | academic_cloud:meta-llama-3.1-8b-instruct | academic_cloud:apertus-70b-instruct-2509 | Agent B | 0.8 |
| 20260722_132503_570771_30912_benchmark | ai_assignments | Argument | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent B | 0.8 |
| 20260722_132503_570771_30912_benchmark | ai_assignments | Deliberative | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent B | 0.8 |
| 20260722_132503_570771_30912_benchmark | ai_assignments | Evidence | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Tie | 1.0 |
| 20260722_132503_570771_30912_benchmark | ai_assignments | Holistic | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:apertus-70b-instruct-2509 | Agent B | 0.8 |
| 20260722_132524_659108_35372_benchmark | ai_assignments | Argument | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:meta-llama-3.1-8b-instruct | Agent A | 0.8 |
| 20260722_132524_659108_35372_benchmark | ai_assignments | Deliberative | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:meta-llama-3.1-8b-instruct | Agent A | 0.8 |
| 20260722_132524_659108_35372_benchmark | ai_assignments | Evidence | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:meta-llama-3.1-8b-instruct | Tie | 1.0 |
| 20260722_132524_659108_35372_benchmark | ai_assignments | Holistic | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:meta-llama-3.1-8b-instruct | Agent A | 0.8 |
| 20260722_132539_675669_25364_benchmark | ai_assignments | Argument | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260722_132539_675669_25364_benchmark | ai_assignments | Deliberative | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.9 |
| 20260722_132539_675669_25364_benchmark | ai_assignments | Evidence | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260722_132539_675669_25364_benchmark | ai_assignments | Holistic | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260722_132602_088278_17268_benchmark | ai_assignments | Argument | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:meta-llama-3.1-8b-instruct | Agent B | 0.8 |
| 20260722_132602_088278_17268_benchmark | ai_assignments | Deliberative | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:meta-llama-3.1-8b-instruct | Agent B | 0.8 |
| 20260722_132602_088278_17268_benchmark | ai_assignments | Evidence | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:meta-llama-3.1-8b-instruct | Agent B | 0.8 |
| 20260722_132602_088278_17268_benchmark | ai_assignments | Holistic | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:meta-llama-3.1-8b-instruct | Agent B | 0.8 |
| 20260722_132622_407833_34316_benchmark | ai_assignments | Argument | a_first | academic_cloud:meta-llama-3.1-8b-instruct | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.9 |
| 20260722_132622_407833_34316_benchmark | ai_assignments | Deliberative | a_first | academic_cloud:meta-llama-3.1-8b-instruct | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.9 |
| 20260722_132622_407833_34316_benchmark | ai_assignments | Evidence | a_first | academic_cloud:meta-llama-3.1-8b-instruct | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 1.0 |
| 20260722_132622_407833_34316_benchmark | ai_assignments | Holistic | a_first | academic_cloud:meta-llama-3.1-8b-instruct | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.9 |
| 20260722_132651_338874_5984_benchmark | ai_assignments | Argument | b_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 1.0 |
| 20260722_132651_338874_5984_benchmark | ai_assignments | Deliberative | b_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 1.0 |
| 20260722_132651_338874_5984_benchmark | ai_assignments | Evidence | b_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 1.0 |
| 20260722_132651_338874_5984_benchmark | ai_assignments | Holistic | b_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 1.0 |
| 20260722_134047_384650_30328_benchmark | ai_assignments | Argument | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:glm-4.7 | Agent B | 0.9 |
| 20260722_134047_384650_30328_benchmark | ai_assignments | Deliberative | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:glm-4.7 | Agent B | 0.8 |
| 20260722_134047_384650_30328_benchmark | ai_assignments | Evidence | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:glm-4.7 | Agent B | 0.8 |
| 20260722_134047_384650_30328_benchmark | ai_assignments | Holistic | a_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:glm-4.7 | Agent B | 0.8 |
| 20260722_134047_384650_30328_benchmark | ai_assignments | Argument | a_first | academic_cloud:glm-4.7 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.85 |
| 20260722_134047_384650_30328_benchmark | ai_assignments | Deliberative | a_first | academic_cloud:glm-4.7 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260722_134047_384650_30328_benchmark | ai_assignments | Holistic | a_first | academic_cloud:glm-4.7 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260722_134047_384650_30328_benchmark | ai_assignments | Deliberative | b_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:glm-4.7 | Agent B | 0.8 |
| 20260722_134047_384650_30328_benchmark | ai_assignments | Evidence | b_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:glm-4.7 | Agent B | 0.8 |
| 20260722_134047_384650_30328_benchmark | ai_assignments | Holistic | b_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:glm-4.7 | Agent B | 0.8 |
| 20260722_134047_384650_30328_benchmark | ai_assignments | Argument | b_first | academic_cloud:glm-4.7 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent A | 0.85 |
| 20260722_134047_384650_30328_benchmark | ai_assignments | Deliberative | b_first | academic_cloud:glm-4.7 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent A | 0.85 |
| 20260722_134047_384650_30328_benchmark | ai_assignments | Holistic | b_first | academic_cloud:glm-4.7 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent A | 0.8 |
| 20260722_134456_583102_20384_benchmark | ai_assignments | Evidence | a_first | academic_cloud:glm-4.7 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent A | 0.8 |
| 20260722_134521_548713_11400_benchmark | ai_assignments | Evidence | b_first | academic_cloud:glm-4.7 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent A | 0.8 |
| 20260722_134610_864163_36488_benchmark | ai_assignments | Argument | b_first | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:glm-4.7 | Agent B | 0.8 |
