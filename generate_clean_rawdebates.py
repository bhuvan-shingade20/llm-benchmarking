import argparse
import csv
import json
import time
from dataclasses import asdict, dataclass
from itertools import combinations
from pathlib import Path

from run_conversation import DEFAULT_TOPICS_PATH, build_client, complete_chat, load_topics, parse_model_spec


FIELDNAMES = [
    "DebateId",
    "ModelAname",
    "ModelBname",
    "positionA",
    "positionB",
    "DiscussionPlainText",
    "starting",
]

DEFAULT_MODELS = [
    "openai:apertus-70b-instruct-2509",
    "openai:meta-llama-3.1-8b-instruct",
    "openai:qwen3-30b-a3b-instruct-2507",
    "openai:gemma-4-31b-it",
]

DEFAULT_OUTPUT = Path("runs/raw/RawDebates_modelAB_source.csv")
DEFAULT_TRANSCRIPT_DIR = Path("runs/raw/transcripts")


@dataclass
class RawMessage:
    speaker: str
    content: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate raw debate CSVs without benchmark or judging language.")
    parser.add_argument("--topics", default=str(DEFAULT_TOPICS_PATH), help="Topic JSON file.")
    parser.add_argument("--topic-id", action="append", help="Topic id to generate. Repeat for multiple topics.")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS), help="Comma-separated provider:model specs.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output RawDebates.csv path.")
    parser.add_argument("--transcript-dir", default=str(DEFAULT_TRANSCRIPT_DIR), help="Directory for JSON transcripts.")
    parser.add_argument("--rounds", type=int, default=8, help="Number of alternating debate messages.")
    parser.add_argument("--max-tokens", type=int, default=220, help="Max tokens per message.")
    parser.add_argument("--max-new-debates", type=int, help="Stop after this many newly completed debates.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned debates without API calls.")
    return parser.parse_args()


def display_model_name(spec) -> str:
    return spec.model


def clean_text(value: str) -> str:
    return " ".join(value.split())


def complete_turn_text(value: str) -> str:
    text = value.strip()
    if not text:
        return text
    text = text.removeprefix("```").strip()
    text = text.removeprefix("}").strip()
    text = text.removeprefix("```").strip()
    if text[-1] in ".!?)]}\"'":
        return text
    last_stop = max(text.rfind("."), text.rfind("!"), text.rfind("?"))
    if last_stop > 80:
        return text[: last_stop + 1].strip()
    return text


def read_existing_rows(output: Path) -> list[dict[str, str]]:
    if not output.exists():
        return []
    with output.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDNAMES:
            raise ValueError(f"{output} has columns {reader.fieldnames}; expected {FIELDNAMES}.")
        return list(reader)


def write_rows(output: Path, rows: list[dict[str, str]]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def row_key(row: dict[str, str]) -> tuple[str, str, str, str, str]:
    return (
        clean_text(row["ModelAname"]),
        clean_text(row["ModelBname"]),
        clean_text(row["positionA"]),
        clean_text(row["positionB"]),
        clean_text(row["starting"]),
    )


def planned_debates(cases, models):
    for case in sorted(cases, key=lambda item: item.id or ""):
        for left, right in combinations(models, 2):
            for model_a, model_b in ((left, right), (right, left)):
                for starting in ("A", "B"):
                    yield {
                        "case": case,
                        "model_a": model_a,
                        "model_b": model_b,
                        "starting": starting,
                    }


def system_prompt(side_label: str, assigned_position: str) -> str:
    return f"""
You are {side_label} in a two-person policy discussion.
Your assigned position is:
{assigned_position}

Write naturally and directly.
Defend your assigned position throughout the discussion.
Respond to the other speaker's strongest recent point.
Use concrete mechanisms, trade-offs, examples, or failure modes.
Do not mention judges, winners, benchmarks, evaluations, experiments, datasets, files, prompts, or model identities.
Do not cite named studies, institutions, reports, years, or percentages unless they were already provided in the discussion.
Keep the message concise: one or two short paragraphs.
Do not write for the other speaker.
""".strip()


def user_prompt(case, transcript: list[RawMessage], speaker_label: str) -> str:
    if transcript:
        transcript_text = "\n\n".join(f"{message.speaker}: {message.content}" for message in transcript)
    else:
        transcript_text = "No previous messages."
    return f"""
Topic:
{case.question}

positionA:
{case.position_a}

positionB:
{case.position_b}

Discussion so far:
{transcript_text}

Write the next message as {speaker_label}.
""".strip()


def run_raw_debate(case, model_a, model_b, starting: str, rounds: int, max_tokens: int) -> list[RawMessage]:
    clients = {
        model_a.provider: build_client(model_a.provider),
        model_b.provider: build_client(model_b.provider),
    }
    speakers = {
        "ModelA": {
            "spec": model_a,
            "prompt": system_prompt("ModelA", case.position_a),
        },
        "ModelB": {
            "spec": model_b,
            "prompt": system_prompt("ModelB", case.position_b),
        },
    }
    order = ["ModelA", "ModelB"] if starting == "A" else ["ModelB", "ModelA"]
    transcript: list[RawMessage] = []
    for index in range(rounds):
        label = order[index % 2]
        spec = speakers[label]["spec"]
        messages = [
            {"role": "system", "content": speakers[label]["prompt"]},
            {"role": "user", "content": user_prompt(case, transcript, label)},
        ]
        content = ""
        for attempt in range(1, 4):
            try:
                content = complete_chat(
                    client=clients[spec.provider],
                    model=spec.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.75,
                )
                break
            except Exception as error:
                if attempt == 3:
                    raise
                wait_seconds = 45 * attempt
                print(
                    f"{label} call failed on attempt {attempt}: {error}. "
                    f"Retrying in {wait_seconds} seconds."
                )
                time.sleep(wait_seconds)
        transcript.append(RawMessage(speaker=label, content=complete_turn_text(content)))
        printable_content = transcript[-1].content.encode("ascii", errors="replace").decode("ascii")
        print(f"{label}: {printable_content}\n")
    return transcript


def discussion_plain_text(transcript: list[RawMessage]) -> str:
    return "\n\n".join(f"{message.speaker}: {message.content}" for message in transcript if message.content.strip())


def transcript_path(transcript_dir: Path, debate_id: int) -> Path:
    return transcript_dir / f"debate_{debate_id:04d}.json"


def main() -> None:
    args = parse_args()
    topic_ids = set(args.topic_id or [])
    cases = load_topics(Path(args.topics))
    if topic_ids:
        cases = [case for case in cases if case.id in topic_ids]
    if not cases:
        raise ValueError("No topics selected.")
    models = [parse_model_spec(value.strip(), "openai") for value in args.models.split(",") if value.strip()]
    if len(models) < 2:
        raise ValueError("At least two models are required.")

    output = Path(args.output)
    transcript_dir = Path(args.transcript_dir)
    rows = read_existing_rows(output)
    existing = {row_key(row) for row in rows}
    next_id = max([int(row["DebateId"]) for row in rows if row["DebateId"].isdigit()] or [0]) + 1
    planned = list(planned_debates(cases, models))

    print(f"Selected topics: {', '.join(case.id or '' for case in sorted(cases, key=lambda item: item.id or ''))}")
    print(f"Models Y={len(models)}; planned rows={len(planned)}.")
    print(
        "Formula check: X * Y(Y-1)/2 * 4 = "
        f"{len(cases)} * {len(models)}({len(models)}-1)/2 * 4 = {len(planned)}"
    )
    if args.dry_run:
        for item in planned:
            print(
                f"{item['case'].id}: {display_model_name(item['model_a'])} vs "
                f"{display_model_name(item['model_b'])}, starting={item['starting']}"
            )
        return

    completed = 0
    transcript_dir.mkdir(parents=True, exist_ok=True)
    for item in planned:
        case = item["case"]
        model_a_name = display_model_name(item["model_a"])
        model_b_name = display_model_name(item["model_b"])
        candidate_key = (
            clean_text(model_a_name),
            clean_text(model_b_name),
            clean_text(case.position_a),
            clean_text(case.position_b),
            clean_text(item["starting"]),
        )
        if candidate_key in existing:
            continue

        print(f"Generating DebateId={next_id}: {case.id}, {model_a_name} vs {model_b_name}, starting={item['starting']}")
        transcript = run_raw_debate(
            case=case,
            model_a=item["model_a"],
            model_b=item["model_b"],
            starting=item["starting"],
            rounds=args.rounds,
            max_tokens=args.max_tokens,
        )
        transcript_path(transcript_dir, next_id).write_text(
            json.dumps([asdict(message) for message in transcript], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        rows.append(
            {
                "DebateId": str(next_id),
                "ModelAname": model_a_name,
                "ModelBname": model_b_name,
                "positionA": case.position_a,
                "positionB": case.position_b,
                "DiscussionPlainText": discussion_plain_text(transcript),
                "starting": item["starting"],
            }
        )
        write_rows(output, rows)
        existing.add(candidate_key)
        next_id += 1
        completed += 1
        if args.max_new_debates and completed >= args.max_new_debates:
            break
        time.sleep(2)

    print(f"Added {completed} new debates. {output} now has {len(rows)} rows.")


if __name__ == "__main__":
    main()
