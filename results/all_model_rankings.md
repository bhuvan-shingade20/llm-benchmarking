# Model Ranking Summary (All Runs)

Generated from 38 valid judge evaluations across 16 benchmark result files.
Skipped 10 rows with judge parse errors, run errors, or missing model fields.
Models currently tracked: 9.
Valid benchmark run IDs included: 13.

## Mentor Summary

| Point | Current Status |
|-------|----------------|
| Proper result storage | CSV/JSON summaries are saved in `results/`; transcripts are saved in `results/conversations/`. |
| Mode 1 single assignment | Implemented as `--benchmark-mode single`; included in the result set. |
| Mode 2 paired role reversal | Implemented as `--benchmark-mode paired`; included in the result set. |
| Position-order bias control | Implemented as `--speaker-order balanced`, which runs both `a_first` and `b_first`. |
| Judge protocols | `winner_only`, `detailed`, and `both` are implemented; one `both` run exposed a malformed detailed JSON response, which is tracked as a parse error. |
| Provider diversity | Academic Cloud and Ollama runs are both included; mixed-provider debates are included. |
| All-runs leaderboard | This file aggregates every `results/*_results.csv` file and labels legacy unprefixed rows as `academic_cloud`. |

## Key Findings For Discussion

| Finding | Evidence In Current Runs | Mentor Feedback Needed |
|---------|--------------------------|------------------------|
| Early Position B dominance was probably structural. | Legacy `a_first` rows show Agent B winning most often, while balanced runs are less one-sided. | Should we exclude legacy rows from the final paper leaderboard or keep them as a bias-detection pilot? |
| Academic Cloud models currently outperform local 3B Ollama models. | Academic Cloud has a positive aggregate win rate; Ollama local models mostly lose or tie in mixed runs. | Is this comparison fair, or should local models be benchmarked in a separate tier? |
| Judge mode matters operationally. | `winner_only` is robust; one `detailed` response from Gemma had malformed JSON despite containing a clear winner. | Should detailed judging be retried on parse failure or replaced with stricter JSON-schema enforcement? |
| Some Academic Cloud endpoints are unstable or slow. | `qwen3.5-122b-a10b` and `teuken-7b-instruct-research` produced empty/500 responses; one `devstral`/`glm` run timed out after saving partial results. | Should unreliable endpoints be excluded or reported as reliability metrics? |
| Current sample size is still small. | Rankings are based on prototype smoke tests across a limited number of topics and judges. | How many topics/runs per model pair are enough for mentor-ready conclusions? |


## Overall Model Ranking

| Rank | Model | Provider | Debates | Wins | Losses | Ties | Win Rate | Avg Overall | Avg Factfulness | Avg Groundedness | Avg Confidence |
|------|-------|----------|---------|------|--------|------|----------|-------------|-----------------|------------------|----------------|
| 1 | glm-4.7 | academic_cloud | 2 | 2 | 0 | 0 | 1.00 | N/A | N/A | N/A | 0.80 |
| 2 | gemma-4-31b-it | academic_cloud | 4 | 3 | 1 | 0 | 0.75 | N/A | N/A | N/A | 0.95 |
| 3 | qwen3-30b-a3b-instruct-2507 | academic_cloud | 18 | 11 | 7 | 0 | 0.61 | 7.50 | 8.50 | 9.14 | 0.82 |
| 4 | apertus-70b-instruct-2509 | academic_cloud | 11 | 6 | 5 | 0 | 0.55 | 8.00 | 9.00 | 9.00 | 0.87 |
| 5 | mistral-large-3-675b-instruct-2512 | academic_cloud | 16 | 8 | 8 | 0 | 0.50 | 7.64 | 8.57 | 9.21 | 0.82 |
| 6 | meta-llama-3.1-8b-instruct | academic_cloud | 8 | 4 | 4 | 0 | 0.50 | N/A | N/A | N/A | 0.80 |
| 7 | qwen2.5:3b | ollama | 6 | 3 | 2 | 1 | 0.50 | N/A | N/A | N/A | 0.82 |
| 8 | devstral-2-123b-instruct-2512 | academic_cloud | 2 | 0 | 2 | 0 | 0.00 | N/A | N/A | N/A | 0.80 |
| 9 | llama3.2:3b | ollama | 9 | 0 | 8 | 1 | 0.00 | 3.00 | 8.00 | 9.00 | 0.88 |

## Per-Provider Summary

| Provider | Total Debates | Wins | Losses | Ties | Win Rate |
|----------|---------------|------|--------|------|----------|
| academic_cloud | 61 | 34 | 27 | 0 | 0.56 |
| ollama | 15 | 3 | 10 | 2 | 0.20 |

## Models Tested

| Model | Provider |
|-------|----------|
| glm-4.7 | academic_cloud |
| gemma-4-31b-it | academic_cloud |
| qwen3-30b-a3b-instruct-2507 | academic_cloud |
| apertus-70b-instruct-2509 | academic_cloud |
| mistral-large-3-675b-instruct-2512 | academic_cloud |
| meta-llama-3.1-8b-instruct | academic_cloud |
| qwen2.5:3b | ollama |
| devstral-2-123b-instruct-2512 | academic_cloud |
| llama3.2:3b | ollama |

## Benchmark Mode Coverage

| Benchmark Mode | Debates | Agent A Wins | Agent B Wins | Ties |
|----------------|---------|--------------|--------------|------|
| legacy | 13 | 1 | 12 | 0 |
| paired | 14 | 6 | 8 | 0 |
| single | 11 | 1 | 9 | 1 |

## Judge Mode Coverage

| Judge Mode | Valid Evaluations | Agent A Wins | Agent B Wins | Ties |
|------------|-------------------|--------------|--------------|------|
| detailed | 2 | 0 | 2 | 0 |
| legacy | 13 | 1 | 12 | 0 |
| winner_only | 23 | 7 | 15 | 1 |

## Position Win Rates

| Position | Debates | Wins | Win Rate |
|----------|---------|------|----------|
| Position A | 38 | 8 | 0.21 |
| Position B | 38 | 29 | 0.76 |

## Speaker Order Effects

| Speaker Order | Debates | Agent A Wins | Agent B Wins | Ties |
|---------------|---------|--------------|--------------|------|
| a_first | 10 | 3 | 6 | 1 |
| a_first (legacy) | 19 | 2 | 17 | 0 |
| b_first | 9 | 3 | 6 | 0 |

## Per-Topic Summary

| Topic | Debates | Decisive Wins |
|-------|---------|---------------|
| ai_assignments | 9 | 8 |
| assessment_design | 5 | 5 |
| cultural_repatriation | 4 | 4 |
| public_software | 5 | 5 |
| remote_work | 7 | 7 |
| right_to_be_forgotten | 4 | 4 |
| urban_density_zoning | 4 | 4 |

## Recent Benchmark Runs

| Run ID | Valid Evaluations | Topics | Models | Benchmark Modes | Judge Modes |
|--------|-------------------|--------|--------|-----------------|-------------|
| 20260710_130658_benchmark | 4 | ai_assignments | academic_cloud:apertus-70b-instruct-2509, academic_cloud:meta-llama-3.1-8b-instruct | paired | winner_only |
| 20260710_130842_349342_benchmark | 4 | remote_work | academic_cloud:apertus-70b-instruct-2509, academic_cloud:gemma-4-31b-it | paired | winner_only |
| 20260710_131647_627729_benchmark | 4 | assessment_design | academic_cloud:meta-llama-3.1-8b-instruct, ollama:qwen2.5:3b | paired | winner_only |
| 20260710_131947_642743_benchmark | 3 | public_software | academic_cloud:apertus-70b-instruct-2509, ollama:llama3.2:3b | single | detailed, winner_only |
| 20260710_132158_682763_benchmark | 2 | remote_work | academic_cloud:devstral-2-123b-instruct-2512, academic_cloud:glm-4.7 | paired | winner_only |
| 20260710_133724_435070_benchmark | 2 | ai_assignments | ollama:llama3.2:3b, ollama:qwen2.5:3b | single | winner_only |

## Reliability Notes

| Issue | Count / Evidence | Handling |
|-------|------------------|----------|
| Invalid or failed rows | 10 rows skipped | Kept in raw CSV/JSON but excluded from win/loss rankings. |
| Malformed detailed judge JSON | Observed in a `judge-mode both` run | Winner-only result remains usable; detailed row is skipped in all-runs ranking. |
| Slow or unstable endpoints | `qwen3.5-122b-a10b`, `teuken-7b-instruct-research`, and a partial `devstral`/`glm` run showed reliability issues | Treat endpoint reliability as a separate experimental observation. |
| Legacy position-order bias | Older rows lack `speaker_order` and default to `a_first (legacy)` | Use balanced speaker-order runs for future conclusions. |

## Suggested Questions For Mentor

1. Should the final leaderboard exclude legacy `a_first` pilot rows and use only balanced speaker-order runs?
2. Should Academic Cloud and Ollama/local models be compared in one leaderboard or separate tiers?
3. Should malformed detailed judge outputs be retried automatically with a stricter JSON prompt?
4. How many topics and repeated runs are enough before claiming stable model rankings?
5. Should model reliability failures count as a benchmark metric separate from persuasion quality?

## Individual Valid Debates

| Run ID | Topic | Speaker Order | Position A Model | Position B Model | Winner | Confidence |
|--------|-------|---------------|------------------|------------------|--------|------------|
| 20260616_190909_benchmark | ai_assignments | a_first (legacy) | academic_cloud:mistral-large-3-675b-instruct-2512 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.85 |
| 20260616_200632_benchmark | cultural_repatriation | a_first (legacy) | academic_cloud:mistral-large-3-675b-instruct-2512 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260616_200632_benchmark | cultural_repatriation | a_first (legacy) | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:mistral-large-3-675b-instruct-2512 | Agent B | 0.8 |
| 20260616_200632_benchmark | cultural_repatriation | a_first (legacy) | academic_cloud:mistral-large-3-675b-instruct-2512 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260616_200632_benchmark | cultural_repatriation | a_first (legacy) | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:mistral-large-3-675b-instruct-2512 | Agent B | 0.9 |
| 20260616_200632_benchmark | right_to_be_forgotten | a_first (legacy) | academic_cloud:mistral-large-3-675b-instruct-2512 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260616_200632_benchmark | right_to_be_forgotten | a_first (legacy) | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:mistral-large-3-675b-instruct-2512 | Agent B | 0.8 |
| 20260616_200632_benchmark | right_to_be_forgotten | a_first (legacy) | academic_cloud:mistral-large-3-675b-instruct-2512 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent A | 0.8 |
| 20260616_200632_benchmark | right_to_be_forgotten | a_first (legacy) | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:mistral-large-3-675b-instruct-2512 | Agent B | 0.8 |
| 20260616_200632_benchmark | urban_density_zoning | a_first (legacy) | academic_cloud:mistral-large-3-675b-instruct-2512 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260616_200632_benchmark | urban_density_zoning | a_first (legacy) | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:mistral-large-3-675b-instruct-2512 | Agent B | 0.8 |
| 20260616_200632_benchmark | urban_density_zoning | a_first (legacy) | academic_cloud:mistral-large-3-675b-instruct-2512 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260616_200632_benchmark | urban_density_zoning | a_first (legacy) | academic_cloud:qwen3-30b-a3b-instruct-2507 | academic_cloud:mistral-large-3-675b-instruct-2512 | Agent B | 0.8 |
| 20260627_025752_benchmark | ai_assignments | a_first (legacy) | ollama:llama3.2:3b | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.9 |
| 20260627_034300_benchmark | ai_assignments | a_first (legacy) | ollama:llama3.2:3b | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.9 |
| 20260627_034339_benchmark | remote_work | a_first (legacy) | academic_cloud:qwen3-30b-a3b-instruct-2507 | ollama:llama3.2:3b | Agent A | 0.8 |
| 20260627_034418_benchmark | assessment_design | a_first (legacy) | ollama:llama3.2:3b | academic_cloud:mistral-large-3-675b-instruct-2512 | Agent B | 1.0 |
| 20260627_035412_benchmark | public_software | a_first (legacy) | academic_cloud:mistral-large-3-675b-instruct-2512 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260627_035412_benchmark | public_software | a_first (legacy) | academic_cloud:mistral-large-3-675b-instruct-2512 | academic_cloud:qwen3-30b-a3b-instruct-2507 | Agent B | 0.8 |
| 20260710_130658_benchmark | ai_assignments | a_first | academic_cloud:meta-llama-3.1-8b-instruct | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.8 |
| 20260710_130658_benchmark | ai_assignments | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:meta-llama-3.1-8b-instruct | Agent B | 0.8 |
| 20260710_130658_benchmark | ai_assignments | b_first | academic_cloud:meta-llama-3.1-8b-instruct | academic_cloud:apertus-70b-instruct-2509 | Agent B | 0.8 |
| 20260710_130658_benchmark | ai_assignments | b_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:meta-llama-3.1-8b-instruct | Agent A | 0.8 |
| 20260710_130842_349342_benchmark | remote_work | a_first | academic_cloud:gemma-4-31b-it | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.95 |
| 20260710_130842_349342_benchmark | remote_work | a_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:gemma-4-31b-it | Agent B | 0.95 |
| 20260710_130842_349342_benchmark | remote_work | b_first | academic_cloud:gemma-4-31b-it | academic_cloud:apertus-70b-instruct-2509 | Agent A | 0.95 |
| 20260710_130842_349342_benchmark | remote_work | b_first | academic_cloud:apertus-70b-instruct-2509 | academic_cloud:gemma-4-31b-it | Agent A | 0.95 |
| 20260710_131647_627729_benchmark | assessment_design | a_first | ollama:qwen2.5:3b | academic_cloud:meta-llama-3.1-8b-instruct | Agent B | 0.8 |
| 20260710_131647_627729_benchmark | assessment_design | a_first | academic_cloud:meta-llama-3.1-8b-instruct | ollama:qwen2.5:3b | Agent B | 0.8 |
| 20260710_131647_627729_benchmark | assessment_design | b_first | ollama:qwen2.5:3b | academic_cloud:meta-llama-3.1-8b-instruct | Agent B | 0.8 |
| 20260710_131647_627729_benchmark | assessment_design | b_first | academic_cloud:meta-llama-3.1-8b-instruct | ollama:qwen2.5:3b | Agent B | 0.8 |
| 20260710_131947_642743_benchmark | public_software | a_first | ollama:llama3.2:3b | academic_cloud:apertus-70b-instruct-2509 | Agent B | 0.8 |
| 20260710_131947_642743_benchmark | public_software | b_first | ollama:llama3.2:3b | academic_cloud:apertus-70b-instruct-2509 | Agent B | 0.9 |
| 20260710_131947_642743_benchmark | public_software | b_first | ollama:llama3.2:3b | academic_cloud:apertus-70b-instruct-2509 | Agent B | 0.9 |
| 20260710_132158_682763_benchmark | remote_work | a_first | academic_cloud:devstral-2-123b-instruct-2512 | academic_cloud:glm-4.7 | Agent B | 0.8 |
| 20260710_132158_682763_benchmark | remote_work | a_first | academic_cloud:glm-4.7 | academic_cloud:devstral-2-123b-instruct-2512 | Agent A | 0.8 |
| 20260710_133724_435070_benchmark | ai_assignments | a_first | ollama:llama3.2:3b | ollama:qwen2.5:3b | Tie | 0.8 |
| 20260710_133724_435070_benchmark | ai_assignments | b_first | ollama:llama3.2:3b | ollama:qwen2.5:3b | Agent B | 0.9 |
