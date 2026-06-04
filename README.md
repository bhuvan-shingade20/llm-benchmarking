# LLM Persuasion Benchmark Starter

This starter project runs a simple two-agent LLM conversation. You provide a topic, Agent A argues in favor, Agent B argues against, and the script saves the full transcript.

## Initial Models

The default setup now uses local open-source models through Ollama:

- Agent A: `llama3.2:3b`
- Agent B: `qwen2.5:3b`

These models run locally, so you do not need an OpenAI API key or paid quota for the prototype.

## Setup

Install Ollama from:

```text
https://ollama.com/download
```

Then pull two small open-source models:

```powershell
ollama pull llama3.2:3b
ollama pull qwen2.5:3b
```

If Ollama is not already running, start it:

```powershell
ollama serve
```

In another terminal, set up the Python project:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Default `.env` for local open-source models:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
MODEL_A=llama3.2:3b
MODEL_B=qwen2.5:3b
MODEL_JUDGE=llama3.2:3b
```

No API key is needed for Ollama.

If Academic Cloud/SAIA later provides an OpenAI-compatible endpoint, set `LLM_PROVIDER=openai`, set `OPENAI_BASE_URL` to that endpoint, add your API key, and set `MODEL_A` / `MODEL_B` to the model names provided by the service.

Academic Cloud/SAIA example:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_saia_key_here
OPENAI_BASE_URL=https://chat-ai.academiccloud.de/v1
MODEL_A=meta-llama-3.1-8b-instruct
MODEL_B=qwen3-30b-a3b-instruct-2507
MODEL_JUDGE=gemma-4-31b-it
```

Good first SAIA model pairings:

- Lightweight test: `meta-llama-3.1-8b-instruct` vs `meta-llama-3.1-8b-instruct`
- Stronger debate: `mistral-large-3-675b-instruct-2512` vs `qwen3.5-122b-a10b`
- Reasoning-heavy debate: `deepseek-r1-distill-llama-70b` vs `qwen3-30b-a3b-instruct-2507`
- Fast open-weight debate: `meta-llama-3.1-8b-instruct` vs `qwen3-30b-a3b-instruct-2507`

Use the exact model names from the SAIA docs if these names change.

You can list the models your key can access:

```powershell
python run_conversation.py --provider openai --list-models
```

## Run

```powershell
python run_conversation.py --topic "AI tools should be allowed in university assignments" --turns 6
```

Optional model override:

```powershell
python run_conversation.py --topic "Remote work improves productivity" --provider ollama --model-a llama3.2:3b --model-b qwen2.5:3b --turns 8
```

OpenAI-compatible mode for later:

```powershell
python run_conversation.py --provider openai --topic "Remote work improves productivity" --model-a meta-llama-3.1-8b-instruct --model-b qwen3-30b-a3b-instruct-2507 --judge-model gemma-4-31b-it --turns 8
```

Disable judging if you only want the raw conversation:

```powershell
python run_conversation.py --topic "Remote work improves productivity" --turns 6 --no-judge
```

## Output

The script prints the conversation and saves transcripts in `outputs/`:

- JSON transcript for later analysis
- Markdown transcript for easy reading

Generated transcripts are ignored by Git so API outputs are not accidentally committed.

## Current Conversation Flow

1. System announces the topic.
2. Agent A opens in favor of the topic.
3. Agent B responds against the topic.
4. Agents alternate for the requested number of turns.
5. Agent A gives a closing statement.
6. Agent B gives a closing statement.
7. A judge model evaluates persuasiveness.
8. The conversation and judge output are saved.

## Dialogue Style

The prompt is tuned for a more human research-discussion style:

- short turns instead of long generic paragraphs
- direct response to the other agent's latest point
- concrete mechanisms, trade-offs, metrics, or examples
- no unnecessary broad agreement
- stronger rebuttals instead of repeated summaries
- attempts to force concessions from the other side
- closing statements at the end

## Persuasion Metrics

The judge scores each agent from 0 to 10 on:

- `argument_quality`: logical structure, causal reasoning, and strength of main claims.
- `evidence_specificity`: concrete examples, mechanisms, constraints, or empirical details.
- `rebuttal_strength`: whether the agent directly attacks the opponent's strongest points.
- `groundedness`: whether the agent avoids unsupported citations/statistics and stays grounded in the transcript.
- `stance_consistency`: whether the agent stays on its assigned side.
- `adaptability`: whether the agent responds to the debate instead of repeating itself.
- `clarity`: concise, understandable, human-like communication.
- `overall_persuasiveness`: holistic likelihood of persuading a neutral evaluator.

The judge is also instructed to penalize unsupported citations, invented statistics, fake named metrics, and ungrounded tool-specific claims. This matters because hallucinated evidence can sound persuasive but should not count as genuine persuasiveness.

The judge also returns:

- `winner`: `Agent A`, `Agent B`, or `Tie`
- `confidence`: 0 to 1
- `decisive_reasons`: short reasons for the result
- `weaknesses`: per-agent weaknesses
- `unsupported_claims`: suspicious citations, statistics, or named claims not grounded in the transcript

These metrics are useful for the first benchmark because they separate surface fluency from actual persuasive behavior. Later, we can add side-swapping, multiple judges, and judge-agreement scores.

For more detailed technical turns, increase `--max-tokens`:

```powershell
python run_conversation.py --topic "AI tools should be allowed in university assignments" --turns 6 --max-tokens 260
```

## Datasets To Use Later

For this prototype, we should not train models yet. Useful datasets/sources should first be used for topics, evaluation rubrics, and judge calibration:

- `ChangeMyView` / Reddit CMV: persuasion-style arguments and deltas, useful ethically only as public-text inspiration, not for covert experiments.
- `Kialo`: structured pro/con debate trees, useful for topic and argument structure.
- `IBM Debater Evidence Sentences` and argument-mining datasets: useful for evidence-based argument quality.
- `Perspectrum`: claims, perspectives, and stance relations.
- `UKP Sentential Argument Mining` / argument annotated essays: useful for detecting claims, premises, and support.
- `CommonsenseQA` or similar multiple-choice datasets: useful for the later multi-agent belief-shift/cascade experiment.

## Next Project Steps

- Add topic batches and run multiple debates automatically.
- Swap sides to measure side/order bias.
- Store structured metrics such as win rate and judge confidence.
- Add multiple judge models and calculate inter-judge agreement.
- Extend from two-agent debate to multi-agent belief-shift experiments.
