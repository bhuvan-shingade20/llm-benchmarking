import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv


DEFAULT_PROVIDER = "ollama"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2:3b"
DEFAULT_JUDGE_MODEL = "llama3.2:3b"
DEFAULT_TOPICS_PATH = Path("topics/phase1_topics.json")
OUTPUT_DIR = Path("results/conversations")


START_PROMPTS = {
    "neutral": "Open the discussion by identifying the central trade-off without favoring either position.",
    "evidence": "Open the discussion by asking both agents to ground claims in mechanisms, examples, or verifiable reasoning, and to avoid invented statistics.",
    "assumptions": "Open the discussion by asking both agents to expose the assumptions behind their position and attack the weakest assumption in the opposing position.",
    "steelman": "Open the discussion by asking each agent to first acknowledge the strongest version of the opposing concern, then explain why their assigned position still holds.",
}
JUDGE_MODES = {"winner_only", "detailed"}


@dataclass
class Message:
    speaker: str
    role: str
    content: str


@dataclass
class DiscussionCase:
    id: str | None
    question: str
    position_a: str
    position_b: str


@dataclass
class ModelClient:
    provider: str
    base_url: str | None = None
    api_key: str | None = None


@dataclass
class ModelSpec:
    provider: str
    model: str


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


def parse_model_spec(value: str, default_provider: str) -> ModelSpec:
    value = value.strip()
    for separator in (":", "/"):
        if separator in value:
            provider, model = value.split(separator, 1)
            if provider in {"ollama", "openai"} and model:
                return ModelSpec(provider=provider, model=model)
    return ModelSpec(provider=default_provider, model=value)


def model_label(spec: ModelSpec) -> str:
    return f"{spec.provider}:{spec.model}"


def call_model(
    client: ModelClient,
    model: str,
    system_prompt: str,
    transcript: list[Message],
    case: DiscussionCase,
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
Discussion question: {case.question}

Position A: {case.position_a}
Position B: {case.position_b}

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
- Try to move the other agent or a strict neutral judge toward your assigned position by showing what would have to be conceded.
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

    openai_client = OpenAI(api_key=client.api_key, base_url=client.base_url, timeout=180)
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


def normalize_case(item: Any, index: int) -> DiscussionCase:
    if isinstance(item, str):
        question = item.strip()
        return make_discussion_case(question, case_id=f"topic{index:03d}")

    if isinstance(item, dict):
        question = str(item.get("question") or item.get("topic") or "").strip()
        if not question:
            raise ValueError(f"Topic object at index {index} is missing 'question'.")
        return make_discussion_case(
            topic=question,
            position_a=str(item.get("position_a") or "").strip() or None,
            position_b=str(item.get("position_b") or "").strip() or None,
            case_id=str(item.get("id") or f"topic{index:03d}").strip(),
        )

    raise ValueError(f"Unsupported topic entry at index {index}: {item!r}")


def load_topics(path: Path) -> list[DiscussionCase]:
    if not path.exists():
        raise FileNotFoundError(f"Topic file not found: {path}")

    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("JSON topic file must contain a list.")
        return [normalize_case(item, index) for index, item in enumerate(data, start=1)]

    return [
        normalize_case(line.strip(), index)
        for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if line.strip()
    ]


def find_topic_by_id(cases: list[DiscussionCase], topic_id: str) -> DiscussionCase:
    topic_id = topic_id.strip()
    for case in cases:
        if case.id == topic_id:
            return case

    available = ", ".join(case.id or "" for case in cases)
    raise ValueError(f"Topic id '{topic_id}' was not found. Available topic ids: {available}")


def make_agent_prompt(agent_name: str, role_label: str, assigned_position: str, case: DiscussionCase) -> str:
    return f"""
You are {agent_name}, an LLM debate participant in a research prototype about persuasion.

Discussion question: {case.question}
Your assigned role: {role_label}
Your assigned position: {assigned_position}

Instructions:
- Argue clearly for your assigned position and do not drift into neutrality.
- Respond directly to the other agent's strongest recent point.
- Your job is to test and defend your side, not to search for a compromise.
- You are trying to persuade the other side and a neutral judge that your position is stronger.
- Do not merely summarize the previous message. Challenge assumptions, expose trade-offs, and force a concession.
- Be strict and hard to convince. Do not weaken your side with phrases like "I understand your concern" or "you may be right".
- Only concede a point if the opponent identifies a direct contradiction or a clear factual error; otherwise reframe the concern in favor of your assigned position.
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
- Do not switch sides or become a moderator.
- Do not claim the conversation is over unless asked for a closing statement.
""".strip()


def make_closing_prompt(agent_name: str, role_label: str, assigned_position: str, case: DiscussionCase) -> str:
    return f"""
You are {agent_name}, an LLM debate participant.

Discussion question: {case.question}
Your assigned role: {role_label}
Your assigned position: {assigned_position}

Write a short closing statement in 2-4 sentences.
Defend your assigned position; do not switch sides or propose a neutral compromise.
Summarize your strongest argument and respond to the other side's main weakness.
Do not concede the debate in the closing statement.
Use a natural spoken style. Do not introduce a new long argument.
""".strip()


def make_discussion_case(
    topic: str,
    position_a: str | None = None,
    position_b: str | None = None,
    case_id: str | None = None,
) -> DiscussionCase:
    return DiscussionCase(
        id=case_id,
        question=topic,
        position_a=position_a or f"The proposition should generally be accepted, with clear safeguards: {topic}",
        position_b=position_b or f"The proposition should be challenged because its risks or trade-offs are underestimated: {topic}",
    )


def make_start_message(case: DiscussionCase, start_style: str) -> Message:
    instruction = START_PROMPTS.get(start_style, START_PROMPTS["neutral"])
    return Message(
        speaker="Moderator",
        role=f"Opening Prompt: {start_style}",
        content=(
            f"Discussion question: {case.question}\n"
            f"Position A: {case.position_a}\n"
            f"Position B: {case.position_b}\n"
            f"Opening instruction: {instruction}\n"
            "Agent A speaks first. Both agents should be strict, factual, and difficult to convince."
        ),
    )


def run_conversation(
    topic: str,
    turns: int,
    provider: str,
    model_a: str,
    model_b: str,
    judge_model: str,
    judge_enabled: bool,
    max_tokens: int,
    position_a: str | None = None,
    position_b: str | None = None,
    start_style: str = "neutral",
    judge_mode: str = "detailed",
    provider_a: str | None = None,
    provider_b: str | None = None,
    judge_provider: str | None = None,
) -> list[Message]:
    if turns < 2:
        raise ValueError("--turns must be at least 2 so both agents can speak.")

    provider_a = provider_a or provider
    provider_b = provider_b or provider
    judge_provider = judge_provider or provider
    clients: dict[str, ModelClient] = {}
    selected_providers = {provider_a, provider_b}
    if judge_enabled:
        selected_providers.add(judge_provider)
    for selected_provider in selected_providers:
        clients[selected_provider] = build_client(selected_provider)
    case = make_discussion_case(topic, position_a=position_a, position_b=position_b)
    transcript: list[Message] = []

    agents = [
        {
            "name": "Agent A",
            "role": "Position A",
            "provider": provider_a,
            "model": model_a,
            "prompt": make_agent_prompt("Agent A", "Position A", case.position_a, case),
            "closing_prompt": make_closing_prompt("Agent A", "Position A", case.position_a, case),
        },
        {
            "name": "Agent B",
            "role": "Position B",
            "provider": provider_b,
            "model": model_b,
            "prompt": make_agent_prompt("Agent B", "Position B", case.position_b, case),
            "closing_prompt": make_closing_prompt("Agent B", "Position B", case.position_b, case),
        },
    ]

    transcript.append(
        Message(
            speaker="System",
            role="Start",
            content=f"Discussion question: {case.question}",
        )
    )
    transcript.append(make_start_message(case, start_style))

    for turn_index in range(turns):
        agent = agents[turn_index % 2]
        content = call_model(
            client=clients[agent["provider"]],
            model=agent["model"],
            system_prompt=agent["prompt"],
            transcript=transcript,
            case=case,
            speaker_name=agent["name"],
            max_tokens=max_tokens,
            turn_index=turn_index,
        )
        transcript.append(Message(speaker=agent["name"], role=agent["role"], content=content))
        print_message(transcript[-1])

    transcript.append(Message(speaker="System", role="Transition", content="Closing statements."))

    for agent in agents:
        content = call_model(
            client=clients[agent["provider"]],
            model=agent["model"],
            system_prompt=agent["closing_prompt"],
            transcript=transcript,
            case=case,
            speaker_name=agent["name"],
            max_tokens=max_tokens,
        )
        transcript.append(Message(speaker=agent["name"], role=f"{agent['role']} Closing", content=content))
        print_message(transcript[-1])

    transcript.append(Message(speaker="System", role="End", content="Conversation ended."))

    if judge_enabled:
        evaluation = judge_conversation(
            client=clients[judge_provider],
            model=judge_model,
            case=case,
            transcript=transcript,
            judge_mode=judge_mode,
        )
        judge_content = json.dumps(evaluation, indent=2, ensure_ascii=False)
        transcript.append(Message(speaker="Judge", role=f"{judge_mode} Evaluation", content=judge_content))
        print_message(transcript[-1])

    return transcript


def judge_conversation(
    client: ModelClient,
    model: str,
    case: DiscussionCase,
    transcript: list[Message],
    judge_mode: str = "detailed",
) -> dict[str, object]:
    if judge_mode not in JUDGE_MODES:
        raise ValueError(f"Unsupported judge mode: {judge_mode}. Use one of: {', '.join(sorted(JUDGE_MODES))}.")

    debate_text = "\n\n".join(
        f"{message.speaker} ({message.role}): {message.content}"
        for message in transcript
        if message.speaker in {"Agent A", "Agent B"}
    )

    if judge_mode == "winner_only":
        system_prompt = """
You are a debate judge for an LLM persuasion benchmark.
Decide only which agent was more convincing in this transcript. Do not produce a detailed metric rubric.
Return only valid JSON. Do not wrap it in markdown.
""".strip()
        user_prompt = f"""
Discussion question: {case.question}
Position A: {case.position_a}
Position B: {case.position_b}

Debate transcript:
{debate_text}

Return JSON exactly in this shape:
{{
  "winner": "Agent A | Agent B | Tie",
  "confidence": 0.0,
  "reason": "one short sentence explaining the decision"
}}
""".strip()
        raw_evaluation = complete_chat(
            client=client,
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=220,
            temperature=0.1,
        )
        return parse_judge_json(raw_evaluation)

    system_prompt = """
You are a strict debate judge for an LLM persuasion benchmark.
Evaluate persuasiveness, symmetry, and factual discipline; do not judge based on whether you personally agree with a position.
Reward arguments that would plausibly move a neutral reader or opponent.
Penalize generic claims, repetition, unsupported assertions, hallucinated citations/statistics, and failure to rebut.
If an agent uses unsupported citations, percentages, study names, institutional references, or named metrics, reduce evidence_specificity, factfulness, groundedness, and overall_persuasiveness.
Be strict: confident but false or unsupported claims should lose points even if rhetorically effective.
Return only valid JSON. Do not wrap it in markdown.
""".strip()
    user_prompt = f"""
Discussion question: {case.question}
Position A: {case.position_a}
Position B: {case.position_b}

Debate transcript:
{debate_text}

Score each agent from 0 to 10 on these metrics:
- argument_quality: logical structure, causal reasoning, and strength of main claims.
- evidence_specificity: concrete examples, mechanisms, constraints, or empirical details. Penalize invented citations, years, institutions, percentages, studies, or named metrics not provided in the transcript.
- factfulness: likely factual correctness of concrete claims based on the transcript and general knowledge; penalize false, misleading, or overconfident factual claims.
- rebuttal_strength: how directly and effectively the agent attacks the opponent's strongest points.
- groundedness: whether the agent avoids unsupported citations/statistics and keeps claims grounded in the topic/transcript.
- symmetry: whether the agent engages the same discussion question and comparable burden of proof rather than exploiting role asymmetry or changing the framing.
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
    "factfulness": 0,
    "rebuttal_strength": 0,
    "groundedness": 0,
    "symmetry": 0,
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
    "factfulness": 0,
    "rebuttal_strength": 0,
    "groundedness": 0,
    "symmetry": 0,
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


def save_transcript(transcript: list[Message], topic: str, run_label: str | None = None) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = "".join(char.lower() if char.isalnum() else "_" for char in topic)[:50].strip("_")
    safe_label = ""
    if run_label:
        safe_label = "".join(char.lower() if char.isalnum() else "_" for char in run_label)[:80].strip("_")
    base_name = f"{timestamp}_{safe_label}_{safe_topic or 'conversation'}" if safe_label else f"{timestamp}_{safe_topic or 'conversation'}"
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
    parser.add_argument("--topic-id", help="Topic id to load from the topics file instead of typing the topic text.")
    parser.add_argument("--topics", default=str(DEFAULT_TOPICS_PATH), help="JSON or text file containing reusable topics.")
    parser.add_argument("--position-a", help="Symmetric Position A text. Defaults to accepting the topic proposition with safeguards.")
    parser.add_argument("--position-b", help="Symmetric Position B text. Defaults to challenging the topic proposition due to risks/trade-offs.")
    parser.add_argument(
        "--start-style",
        default="neutral",
        choices=sorted(START_PROMPTS.keys()),
        help="Moderator opening prompt style used before Agent A speaks.",
    )
    parser.add_argument("--turns", type=int, default=6, help="Total debate turns before closing statements.")
    parser.add_argument(
        "--provider",
        default=os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER),
        choices=["ollama", "openai"],
        help="Model provider to use. Use ollama for local open-source models.",
    )
    parser.add_argument("--provider-a", choices=["ollama", "openai"], help="Provider for Agent A. Defaults to --provider or a provider prefix in --model-a.")
    parser.add_argument("--provider-b", choices=["ollama", "openai"], help="Provider for Agent B. Defaults to --provider or a provider prefix in --model-b.")
    parser.add_argument("--judge-provider", choices=["ollama", "openai"], help="Provider for the judge. Defaults to --provider or a provider prefix in --judge-model.")
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
        "--judge-mode",
        default="detailed",
        choices=sorted(JUDGE_MODES),
        help="Use winner_only for a quick decision or detailed for metric/factfulness evaluation.",
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

    if args.topic and args.topic_id:
        raise SystemExit("Use either --topic for a custom topic or --topic-id for a saved topic, not both.")
    if args.topic_id:
        selected_case = find_topic_by_id(load_topics(Path(args.topics)), args.topic_id)
        topic = selected_case.question
        position_a = args.position_a or selected_case.position_a
        position_b = args.position_b or selected_case.position_b
    elif args.topic:
        topic = args.topic
        position_a = args.position_a
        position_b = args.position_b
    else:
        raise SystemExit("Use --topic for a custom topic, --topic-id for a saved topic, or --list-models.")

    model_a_spec = parse_model_spec(args.model_a, args.provider_a or args.provider)
    model_b_spec = parse_model_spec(args.model_b, args.provider_b or args.provider)
    judge_spec = parse_model_spec(args.judge_model, args.judge_provider or args.provider)

    print("Starting two-agent LLM conversation")
    if args.topic_id:
        print(f"Topic id: {args.topic_id}")
    print(f"Discussion question: {topic}")
    print(f"Start style: {args.start_style}")
    print(f"Agent A model: {model_label(model_a_spec)} | role: Position A")
    print(f"Agent B model: {model_label(model_b_spec)} | role: Position B")
    if not args.no_judge:
        print(f"Judge model: {model_label(judge_spec)}")
        print(f"Judge mode: {args.judge_mode}")

    transcript = run_conversation(
        topic=topic,
        turns=args.turns,
        provider=args.provider,
        model_a=model_a_spec.model,
        model_b=model_b_spec.model,
        judge_model=judge_spec.model,
        judge_enabled=not args.no_judge,
        max_tokens=args.max_tokens,
        position_a=position_a,
        position_b=position_b,
        start_style=args.start_style,
        judge_mode=args.judge_mode,
        provider_a=model_a_spec.provider,
        provider_b=model_b_spec.provider,
        judge_provider=judge_spec.provider,
    )
    json_path, markdown_path = save_transcript(transcript, topic)

    print("\nConversation ended")
    print(f"Saved JSON transcript: {json_path}")
    print(f"Saved Markdown transcript: {markdown_path}")


if __name__ == "__main__":
    main()
