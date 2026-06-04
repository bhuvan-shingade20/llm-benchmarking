import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv


DEFAULT_PROVIDER = "ollama"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2:3b"
DEFAULT_JUDGE_MODEL = "llama3.2:3b"
OUTPUT_DIR = Path("outputs")


@dataclass
class Message:
    speaker: str
    role: str
    content: str


@dataclass
class ModelClient:
    provider: str
    base_url: str | None = None
    api_key: str | None = None


def build_client(provider: str) -> ModelClient:
    load_dotenv()
    provider = provider.lower()

    if provider == "ollama":
        return ModelClient(
            provider="ollama",
            base_url=os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).rstrip("/"),
        )

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Create a .env file from .env.example and add your API key."
            )
        return ModelClient(
            provider="openai",
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_key=api_key,
        )

    raise ValueError(f"Unsupported provider: {provider}. Use 'ollama' or 'openai'.")


def call_model(
    client: ModelClient,
    model: str,
    system_prompt: str,
    transcript: list[Message],
    topic: str,
    speaker_name: str,
    max_tokens: int,
    turn_index: int | None = None,
) -> str:
    visible_transcript = [message for message in transcript if message.speaker != "System"]
    conversation_context = "\n\n".join(
        f"{message.speaker} ({message.role}): {message.content}" for message in visible_transcript
    )
    if not conversation_context:
        conversation_context = "No previous agent messages. Start the conversation."

    turn_instruction = ""
    if turn_index is not None:
        turn_instruction = f"This is debate turn {turn_index + 1}."

    user_prompt = f"""
Topic: {topic}

Conversation so far:
{conversation_context}

You are {speaker_name}. Write your next message in the conversation.
{turn_instruction}

Requirements:
- Write like a sharp human researcher in a live discussion, not like an essay.
- Use 2 short paragraphs maximum.
- Keep the response around 80-130 words unless a technical point needs slightly more.
- Do not use generic debate openings like "the crux of this debate" or "this is an important issue".
- Attack one concrete weakness in the other agent's last argument. Do not restate their point unless needed in under 12 words.
- Add one technical detail, mechanism, failure mode, or example that makes your side harder to dismiss.
- Try to move the other agent toward your position by showing what they would have to concede.
- Vary your wording. Avoid repeated openings like "Agent A mentioned", "Agent B mentioned", "You are right", or "I agree".
- FORBIDDEN: do not cite studies, institutions, years, percentages, named metrics, datasets, or tool features unless they were provided in the topic or transcript.
- If you need evidence but do not have a source, describe it as a hypothetical or mechanism, not as a factual study.
- Do not start with broad agreement unless you genuinely concede a narrow point.
- Do not refer to the System message as a participant or as making a claim.
- Do not write for the other agent.
""".strip()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    content = complete_chat(client, model, messages, max_tokens=max_tokens, temperature=0.75)

    if not content:
        raise RuntimeError(f"Model {model} returned an empty response.")
    return content.strip()


def complete_chat(
    client: ModelClient,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float,
) -> str:
    if client.provider == "ollama":
        return call_ollama(client, model, messages, max_tokens, temperature)
    return call_openai_compatible(client, model, messages, max_tokens, temperature)


def call_ollama(
    client: ModelClient,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float,
) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    request = Request(
        f"{client.base_url}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=180) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except URLError as error:
        raise RuntimeError(
            "Could not connect to Ollama. Install Ollama, run `ollama serve`, and pull a model "
            "with `ollama pull llama3.2:3b`."
        ) from error

    return response_data.get("message", {}).get("content", "")


def call_openai_compatible(
    client: ModelClient,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float,
) -> str:
    try:
        from openai import NotFoundError, OpenAI
    except ImportError as error:
        raise RuntimeError("Install OpenAI support with `pip install openai`.") from error

    openai_client = OpenAI(api_key=client.api_key, base_url=client.base_url)
    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except NotFoundError as error:
        raise RuntimeError(
            f"Model '{model}' was not found by the OpenAI-compatible API. "
            "For SAIA, run `python run_conversation.py --provider openai --list-models` "
            "and copy one of the returned model IDs into MODEL_A or MODEL_B."
        ) from error
    return response.choices[0].message.content or ""


def list_openai_compatible_models(client: ModelClient) -> list[str]:
    try:
        from openai import OpenAI
    except ImportError as error:
        raise RuntimeError("Install OpenAI support with `pip install openai`.") from error

    openai_client = OpenAI(api_key=client.api_key, base_url=client.base_url)
    models = openai_client.models.list()
    return sorted(model.id for model in models.data)


def make_agent_prompt(agent_name: str, stance: str, topic: str) -> str:
    stance_goal = (
        "prove that the topic should be accepted and implemented under clear rules"
        if stance == "in favor of"
        else "prove that the topic should be rejected or heavily restricted"
    )
    return f"""
You are {agent_name}, an LLM debate participant in a research prototype about persuasion.

Your stance: {stance} the topic.
Topic: {topic}
Your debate goal: {stance_goal}.

Instructions:
- Argue clearly for your assigned stance and do not drift into neutrality.
- Respond directly to the other agent's strongest recent point.
- Your job is to test and defend your side, not to search for a compromise.
- You are trying to persuade the other side and a neutral judge that your position is stronger.
- Do not merely summarize the previous message. Challenge assumptions, expose trade-offs, and force a concession.
- Be assertive. Do not weaken your side with phrases like "I understand your concern" or "you may be right".
- If the opponent raises a valid concern, reframe it as a solvable implementation issue if you are For, or as a structural failure if you are Against.
- Use concise reasoning, concrete examples, and technical details.
- Prefer mechanisms, trade-offs, metrics, failure modes, or empirical examples over generic claims.
- FORBIDDEN: do not cite studies, institutions, years, percentages, named metrics, datasets, or tool-specific features unless they were provided in the topic or transcript.
- If you need evidence but do not have a source, describe it as a hypothetical or mechanism, not as a factual study.
- Sound like a thoughtful person in a live seminar discussion, not like a formal essay.
- Keep each turn compact: 2 short paragraphs maximum.
- If you concede something, make it narrow and then explain why your side still holds.
- Avoid generic openings like "I agree" or "I see where you're coming from" unless followed by a sharp challenge.
- Avoid formulaic references like "Agent A mentioned" or "Agent B mentioned". Reply naturally.
- Stay respectful and avoid personal attacks.
- Do not switch sides.
- Do not claim the conversation is over unless asked for a closing statement.
""".strip()


def make_closing_prompt(agent_name: str, stance: str, topic: str) -> str:
    stance_goal = (
        "make the strongest final case that the topic should be accepted"
        if stance == "in favor of"
        else "make the strongest final case that the topic should be rejected or restricted"
    )
    return f"""
You are {agent_name}, an LLM debate participant.

Your stance: {stance} the topic.
Topic: {topic}
Your closing goal: {stance_goal}.

Write a short closing statement in 2-4 sentences.
Defend your assigned stance; do not switch sides or propose a neutral compromise.
Summarize your strongest argument and respond to the other side's main weakness.
Do not concede the debate in the closing statement.
Use a natural spoken style. Do not introduce a new long argument.
""".strip()


def run_conversation(
    topic: str,
    turns: int,
    provider: str,
    model_a: str,
    model_b: str,
    judge_model: str,
    judge_enabled: bool,
    max_tokens: int,
) -> list[Message]:
    if turns < 2:
        raise ValueError("--turns must be at least 2 so both agents can speak.")

    client = build_client(provider)
    transcript: list[Message] = []

    agents = [
        {
            "name": "Agent A",
            "role": "For",
            "model": model_a,
            "prompt": make_agent_prompt("Agent A", "in favor of", topic),
            "closing_prompt": make_closing_prompt("Agent A", "in favor of", topic),
        },
        {
            "name": "Agent B",
            "role": "Against",
            "model": model_b,
            "prompt": make_agent_prompt("Agent B", "against", topic),
            "closing_prompt": make_closing_prompt("Agent B", "against", topic),
        },
    ]

    transcript.append(
        Message(
            speaker="System",
            role="Start",
            content=f"Conversation topic: {topic}",
        )
    )

    for turn_index in range(turns):
        agent = agents[turn_index % 2]
        content = call_model(
            client=client,
            model=agent["model"],
            system_prompt=agent["prompt"],
            transcript=transcript,
            topic=topic,
            speaker_name=agent["name"],
            max_tokens=max_tokens,
            turn_index=turn_index,
        )
        transcript.append(Message(speaker=agent["name"], role=agent["role"], content=content))
        print_message(transcript[-1])

    transcript.append(Message(speaker="System", role="Transition", content="Closing statements."))

    for agent in agents:
        content = call_model(
            client=client,
            model=agent["model"],
            system_prompt=agent["closing_prompt"],
            transcript=transcript,
            topic=topic,
            speaker_name=agent["name"],
            max_tokens=max_tokens,
        )
        transcript.append(Message(speaker=agent["name"], role=f"{agent['role']} Closing", content=content))
        print_message(transcript[-1])

    transcript.append(Message(speaker="System", role="End", content="Conversation ended."))

    if judge_enabled:
        evaluation = judge_conversation(
            client=client,
            model=judge_model,
            topic=topic,
            transcript=transcript,
        )
        judge_content = json.dumps(evaluation, indent=2, ensure_ascii=False)
        transcript.append(Message(speaker="Judge", role="Persuasion Evaluation", content=judge_content))
        print_message(transcript[-1])

    return transcript


def judge_conversation(
    client: ModelClient,
    model: str,
    topic: str,
    transcript: list[Message],
) -> dict[str, object]:
    debate_text = "\n\n".join(
        f"{message.speaker} ({message.role}): {message.content}"
        for message in transcript
        if message.speaker in {"Agent A", "Agent B"}
    )
    system_prompt = """
You are a strict debate judge for an LLM persuasion benchmark.
Evaluate persuasiveness, not whether you personally agree with the topic.
Reward arguments that would plausibly move a neutral reader or opponent.
Penalize generic claims, repetition, unsupported assertions, hallucinated citations/statistics, and failure to rebut.
If an agent uses unsupported citations, percentages, study names, institutional references, or named metrics, reduce evidence_specificity, groundedness, and overall_persuasiveness.
Return only valid JSON. Do not wrap it in markdown.
""".strip()
    user_prompt = f"""
Topic: {topic}

Debate transcript:
{debate_text}

Score each agent from 0 to 10 on these metrics:
- argument_quality: logical structure, causal reasoning, and strength of main claims.
- evidence_specificity: concrete examples, mechanisms, constraints, or empirical details. Penalize invented citations, years, institutions, percentages, studies, or named metrics not provided in the transcript.
- rebuttal_strength: how directly and effectively the agent attacks the opponent's strongest points.
- groundedness: whether the agent avoids unsupported citations/statistics and keeps claims grounded in the topic/transcript.
- stance_consistency: whether the agent stays on its assigned side without drifting into compromise.
- adaptability: whether the agent evolves its argument in response to the debate instead of repeating itself.
- clarity: concise, understandable, human-like communication.
- overall_persuasiveness: holistic likelihood of persuading a neutral evaluator.

Also provide:
- winner: "Agent A", "Agent B", or "Tie".
- confidence: number from 0 to 1.
- decisive_reasons: 2-4 short reasons for the winner.
- weaknesses: short weakness list for each agent.
- unsupported_claims: any suspicious citation, statistic, named study, named metric, or tool-specific claim not grounded in the transcript.

Return JSON exactly in this shape:
{{
  "winner": "Agent A | Agent B | Tie",
  "confidence": 0.0,
  "agent_a": {{
    "argument_quality": 0,
    "evidence_specificity": 0,
    "rebuttal_strength": 0,
    "groundedness": 0,
    "stance_consistency": 0,
    "adaptability": 0,
    "clarity": 0,
    "overall_persuasiveness": 0,
    "weaknesses": ["..."],
    "unsupported_claims": ["..."]
  }},
  "agent_b": {{
    "argument_quality": 0,
    "evidence_specificity": 0,
    "rebuttal_strength": 0,
    "groundedness": 0,
    "stance_consistency": 0,
    "adaptability": 0,
    "clarity": 0,
    "overall_persuasiveness": 0,
    "weaknesses": ["..."],
    "unsupported_claims": ["..."]
  }},
  "decisive_reasons": ["..."]
}}
""".strip()

    raw_evaluation = complete_chat(
        client=client,
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=900,
        temperature=0.1,
    )
    return parse_judge_json(raw_evaluation)


def parse_judge_json(raw_evaluation: str) -> dict[str, object]:
    cleaned = raw_evaluation.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                pass
    return {
        "winner": "Unable to parse judge output",
        "confidence": 0,
        "raw_output": raw_evaluation,
    }


def print_message(message: Message) -> None:
    print(f"\n{message.speaker} [{message.role}]\n{message.content}\n")


def save_transcript(transcript: list[Message], topic: str) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = "".join(char.lower() if char.isalnum() else "_" for char in topic)[:50].strip("_")
    base_name = f"{timestamp}_{safe_topic or 'conversation'}"
    json_path = OUTPUT_DIR / f"{base_name}.json"
    markdown_path = OUTPUT_DIR / f"{base_name}.md"

    json_path.write_text(
        json.dumps([asdict(message) for message in transcript], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    markdown_lines = [f"# LLM Conversation", "", f"**Topic:** {topic}", ""]
    for message in transcript:
        markdown_lines.extend(
            [f"## {message.speaker} ({message.role})", "", message.content, ""]
        )
    markdown_path.write_text("\n".join(markdown_lines), encoding="utf-8")

    return json_path, markdown_path


def parse_args() -> argparse.Namespace:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run a two-agent LLM conversation on a topic.")
    parser.add_argument("--topic", help="Conversation topic to debate.")
    parser.add_argument("--turns", type=int, default=6, help="Total debate turns before closing statements.")
    parser.add_argument(
        "--provider",
        default=os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER),
        choices=["ollama", "openai"],
        help="Model provider to use. Use ollama for local open-source models.",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available models for the selected provider and exit.",
    )
    parser.add_argument("--model-a", default=os.getenv("MODEL_A", DEFAULT_MODEL), help="Model for Agent A.")
    parser.add_argument("--model-b", default=os.getenv("MODEL_B", DEFAULT_MODEL), help="Model for Agent B.")
    parser.add_argument(
        "--judge-model",
        default=os.getenv("MODEL_JUDGE", os.getenv("MODEL_A", DEFAULT_JUDGE_MODEL)),
        help="Model used to judge persuasion after the debate.",
    )
    parser.add_argument(
        "--no-judge",
        action="store_true",
        help="Disable the persuasion judge step.",
    )
    parser.add_argument("--max-tokens", type=int, default=180, help="Maximum tokens per model response.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.list_models:
        client = build_client(args.provider)
        if client.provider == "openai":
            for model_id in list_openai_compatible_models(client):
                print(model_id)
            return
        print("For Ollama, use `ollama list` to see locally installed models.")
        return

    if not args.topic:
        raise SystemExit("--topic is required unless --list-models is used.")

    print("Starting two-agent LLM conversation")
    print(f"Topic: {args.topic}")
    print(f"Provider: {args.provider}")
    print(f"Agent A model: {args.model_a} | stance: For")
    print(f"Agent B model: {args.model_b} | stance: Against")
    if not args.no_judge:
        print(f"Judge model: {args.judge_model}")

    transcript = run_conversation(
        topic=args.topic,
        turns=args.turns,
        provider=args.provider,
        model_a=args.model_a,
        model_b=args.model_b,
        judge_model=args.judge_model,
        judge_enabled=not args.no_judge,
        max_tokens=args.max_tokens,
    )
    json_path, markdown_path = save_transcript(transcript, args.topic)

    print("\nConversation ended")
    print(f"Saved JSON transcript: {json_path}")
    print(f"Saved Markdown transcript: {markdown_path}")


if __name__ == "__main__":
    main()
