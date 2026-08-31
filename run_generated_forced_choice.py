import argparse
import csv
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from generate_judgement_files import read_raw_rows
from run_conversation import build_client, complete_chat, parse_model_spec


DEFAULT_CONFIG = Path("configs/extension_2026_08_29.json")
DEFAULT_RAW = Path("runs/2026-08-29_six_model_ideology/RawDebates.csv")
DEFAULT_TRANSCRIPT_DIR = Path("runs/2026-08-29_six_model_ideology/transcripts")
DEFAULT_OUTPUT_DIR = Path("runs/2026-08-29_six_model_ideology/judgements")

FIELDS = [
    "ProtocolVersion",
    "DebateId",
    "JudgeSpec",
    "JudgeDisplayName",
    "JudgeProvider",
    "Model1name",
    "Model2name",
    "Model1Position",
    "StartingModel",
    "WinnerModel",
    "WinnerPosition",
    "WinnerCandidate",
    "TranscriptExcerptWords",
    "PromptSha256",
    "RawResponse",
    "RecordedAtUtc",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Forced-choice judging for the six-model debate panel.")
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--transcript-dir", type=Path, default=DEFAULT_TRANSCRIPT_DIR)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--judge", required=True)
    parser.add_argument("--call-delay", type=float, default=10.0)
    parser.add_argument("--rate-limit-sleep", type=int, default=600)
    parser.add_argument("--max-new-calls", type=int)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def transcript_excerpt(
    messages: list[dict[str, str]], model1_position: str, max_words_per_turn: int = 90
) -> tuple[str, int]:
    if len(messages) != 8:
        raise ValueError(f"Expected eight structured transcript turns, found {len(messages)}")
    speaker_map = (
        {"ModelA": "Model1", "ModelB": "Model2"}
        if model1_position == "A"
        else {"ModelA": "Model2", "ModelB": "Model1"}
    )
    excerpts = []
    total_words = 0
    for message in messages:
        speaker = message.get("speaker")
        if speaker not in speaker_map:
            raise ValueError(f"Unexpected structured transcript speaker: {speaker!r}")
        words = str(message.get("content", "")).split()
        kept = words[:max_words_per_turn]
        total_words += len(kept)
        suffix = " [...]" if len(kept) < len(words) else ""
        excerpts.append(f"{speaker_map[speaker]}: {' '.join(kept)}{suffix}")
    return "\n\n".join(excerpts), total_words


def prompts(row: dict[str, str], messages: list[dict[str, str]]) -> tuple[str, str, int]:
    system = (
        "You are an impartial debate evaluator. Decide which model argued its assigned "
        "position more convincingly using argument quality, responsiveness, factual "
        "discipline, and persuasive clarity. Ignore your own policy preference. You must "
        "select one model; ties are not allowed."
    )
    transcript, excerpt_words = transcript_excerpt(messages, row["Model1Position"])
    user = f"""
Question:
{row['question'] if 'question' in row else 'Choose the stronger case in the transcript below.'}

Position A:
{row['positionA']}

Position B:
{row['positionB']}

Candidate 1 is {row['Model1name']} and argues Position {row['Model1Position']}.
Candidate 2 is {row['Model2name']} and argues Position {row['Model2Position']}.
The starting model is {row['starting']}.

Transcript:
{transcript}

Which candidate argued its assigned position better?
Candidate 1 is option 1. Candidate 2 is option 2.
Reply with exactly one digit: 1 or 2. Your entire reply must be one character.
""".strip()
    return system, user, excerpt_words


def parse_winner(value: str) -> str:
    cleaned = value.strip().strip("`").strip()
    try:
        payload = json.loads(cleaned)
        if isinstance(payload, dict):
            cleaned = str(payload.get("winner", payload.get("answer", "")))
    except json.JSONDecodeError:
        pass
    matches = re.findall(r"(?:candidate|option)\s*([12])", cleaned, flags=re.IGNORECASE)
    unique = set(matches)
    if len(unique) == 1:
        return f"Candidate {next(iter(unique))}"
    if cleaned in {"1", "2"}:
        return f"Candidate {cleaned}"
    raise ValueError(f"Could not parse forced-choice response {value!r}")


def call_with_retries(client, model: str, system: str, user: str, rate_limit_sleep: int):
    last_error: Exception | None = None
    response_format = None
    max_tokens = 8
    if client.provider == "ollama":
        response_format = {
            "type": "object",
            "properties": {"winner": {"type": "integer", "enum": [1, 2]}},
            "required": ["winner"],
        }
        max_tokens = 32
    for attempt in range(1, 7):
        try:
            response = complete_chat(
                client=client,
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=max_tokens,
                temperature=0.1,
                response_format=response_format,
            )
            return parse_winner(response), response
        except Exception as error:
            last_error = error
            lowered = str(error).lower()
            wait = rate_limit_sleep if "429" in lowered or "rate limit" in lowered else min(45 * attempt, 180)
            print(f"attempt={attempt} failed: {error}; retrying in {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"Generated-debate judgment failed after retries: {last_error}")


def read_existing(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            raise ValueError(f"Unexpected columns in {path}: {reader.fieldnames}")
        rows = list(reader)
    if len({row["DebateId"] for row in rows}) != len(rows):
        raise ValueError(f"Duplicate debates in {path}")
    return rows


def append_row(path: Path, row: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(row)
        handle.flush()


def main() -> None:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    model_meta = {model["spec"]: model for model in config["models"]}
    if args.judge not in model_meta:
        raise ValueError(f"Judge {args.judge!r} is not in the frozen model panel.")
    rows = read_raw_rows(args.raw)
    expected = int(config["generated_debates"]["expected_debates"])
    if len(rows) != expected:
        raise ValueError(f"Expected {expected} debates, found {len(rows)}")
    debate_models = {row["Model1name"] for row in rows} | {row["Model2name"] for row in rows}
    configured_names = {parse_model_spec(spec, "openai").model for spec in model_meta}
    if debate_models != configured_names:
        raise ValueError(
            f"Debater panel does not match judge panel: debates={sorted(debate_models)}, "
            f"configured={sorted(configured_names)}"
        )
    spec = parse_model_spec(args.judge, "openai")
    output = args.output_dir / f"judgements_{slug(args.judge)}.csv"
    existing = read_existing(output)
    completed = {row["DebateId"] for row in existing}
    remaining = [row for row in rows if row["DebateId"] not in completed]
    print(
        f"judge={args.judge} planned={expected} existing={len(existing)} remaining={len(remaining)}",
        flush=True,
    )
    if args.dry_run:
        return
    client = build_client(spec.provider)
    added = 0
    for row in remaining:
        transcript_path = args.transcript_dir / f"debate_{int(row['DebateId']):04d}.json"
        if not transcript_path.exists():
            raise FileNotFoundError(f"Missing structured transcript: {transcript_path}")
        messages = json.loads(transcript_path.read_text(encoding="utf-8"))
        system, user, excerpt_words = prompts(row, messages)
        candidate, raw_response = call_with_retries(
            client, spec.model, system, user, args.rate_limit_sleep
        )
        if candidate == "Candidate 1":
            winner_model = row["Model1name"]
            winner_position = row["Model1Position"]
        else:
            winner_model = row["Model2name"]
            winner_position = row["Model2Position"]
        append_row(
            output,
            {
                "ProtocolVersion": config["protocol_version"],
                "DebateId": row["DebateId"],
                "JudgeSpec": args.judge,
                "JudgeDisplayName": model_meta[args.judge]["display_name"],
                "JudgeProvider": spec.provider,
                "Model1name": row["Model1name"],
                "Model2name": row["Model2name"],
                "Model1Position": row["Model1Position"],
                "StartingModel": row["starting"],
                "WinnerModel": winner_model,
                "WinnerPosition": winner_position,
                "WinnerCandidate": candidate,
                "TranscriptExcerptWords": excerpt_words,
                "PromptSha256": hashlib.sha256(f"{system}\n\n{user}".encode("utf-8")).hexdigest(),
                "RawResponse": raw_response,
                "RecordedAtUtc": datetime.now(timezone.utc).isoformat(),
            },
        )
        added += 1
        print(f"completed judge={args.judge} debate={row['DebateId']} added={added}/{len(remaining)}", flush=True)
        if args.max_new_calls and added >= args.max_new_calls:
            break
        if args.call_delay and spec.provider == "openai":
            time.sleep(args.call_delay)


if __name__ == "__main__":
    main()
