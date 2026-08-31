import argparse
import csv
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from run_conversation import build_client, complete_chat, parse_model_spec


DEFAULT_INPUT = Path("data/external/poliprop/PoliPropPrepared.jsonl")
DEFAULT_CONFIG = Path("configs/extension_2026_08_29.json")
DEFAULT_OUTPUT_DIR = Path("runs/2026-08-29_poliprop_ideology_annotations")

FIELDS = [
    "ProtocolVersion",
    "DebateId",
    "AnnotatorSpec",
    "PoliticallyRelevant",
    "ProScore",
    "ConScore",
    "Confidence",
    "RawResponse",
    "RecordedAtUtc",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Blindly annotate PoliProp position ideology.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--annotator", required=True)
    parser.add_argument("--call-delay", type=float, default=10.0)
    parser.add_argument("--rate-limit-sleep", type=int, default=600)
    parser.add_argument("--max-new-calls", type=int)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def read_jsonl(path: Path) -> list[dict[str, object]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def prompts(record: dict[str, object]) -> tuple[str, str]:
    system = (
        "You annotate political positions in contemporary United States policy discourse. "
        "Classify ideological direction, not argument quality, factual correctness, or which "
        "position you prefer. Use -2 for strongly liberal, -1 for moderately liberal, 0 for "
        "centrist or not ideologically classifiable, +1 for moderately conservative, and +2 "
        "for strongly conservative."
    )
    user = f"""
Debate proposition:
{record['proposition']}

Pro position: supports the proposition.
Con position: opposes the proposition.

Return one JSON object with exactly these fields:
{{
  "politically_relevant": true,
  "pro_score": -1,
  "con_score": 1,
  "confidence": 0.80
}}

`politically_relevant` must be true or false. Scores must be integers in
[-2, -1, 0, 1, 2]. Confidence must be a number from 0 to 1.
""".strip()
    return system, user


def parse_payload(value: str) -> dict[str, object]:
    cleaned = value.strip().strip("`").strip()
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group(0)
    payload = json.loads(cleaned)
    required = {"politically_relevant", "pro_score", "con_score", "confidence"}
    if set(payload) != required:
        raise ValueError(f"Unexpected annotation fields: {sorted(payload)}")
    if not isinstance(payload["politically_relevant"], bool):
        raise ValueError("politically_relevant must be boolean")
    for key in ("pro_score", "con_score"):
        if not isinstance(payload[key], int) or payload[key] not in {-2, -1, 0, 1, 2}:
            raise ValueError(f"{key} must be an integer from -2 to 2")
    confidence = float(payload["confidence"])
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1")
    payload["confidence"] = confidence
    return payload


def call_with_retries(client, model: str, system: str, user: str, rate_limit_sleep: int):
    last_error: Exception | None = None
    for attempt in range(1, 7):
        try:
            response = complete_chat(
                client=client,
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=180,
                temperature=0.1,
            )
            return parse_payload(response), response
        except Exception as error:
            last_error = error
            lowered = str(error).lower()
            wait = rate_limit_sleep if "429" in lowered or "rate limit" in lowered else min(45 * attempt, 180)
            print(f"attempt={attempt} failed: {error}; retrying in {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"Ideology annotation failed after retries: {last_error}")


def read_existing(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            raise ValueError(f"Unexpected columns in {path}: {reader.fieldnames}")
        rows = list(reader)
    ids = [row["DebateId"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate debate annotations in {path}")
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
    if args.annotator not in config["ideology_annotators"]:
        raise ValueError(f"Annotator {args.annotator!r} is not in the frozen panel.")
    records = read_jsonl(args.input)
    if len(records) != 833:
        raise ValueError(f"Expected 833 debates, found {len(records)}")
    spec = parse_model_spec(args.annotator, "openai")
    output = args.output_dir / f"annotations_{slug(args.annotator)}.csv"
    existing = read_existing(output)
    completed = {int(row["DebateId"]) for row in existing}
    remaining = [record for record in records if int(record["debate_id"]) not in completed]
    print(
        f"annotator={args.annotator} planned=833 existing={len(existing)} remaining={len(remaining)}",
        flush=True,
    )
    if args.dry_run:
        return
    client = build_client(spec.provider)
    added = 0
    for record in remaining:
        system, user = prompts(record)
        payload, raw_response = call_with_retries(
            client, spec.model, system, user, args.rate_limit_sleep
        )
        append_row(
            output,
            {
                "ProtocolVersion": config["protocol_version"],
                "DebateId": record["debate_id"],
                "AnnotatorSpec": args.annotator,
                "PoliticallyRelevant": int(payload["politically_relevant"]),
                "ProScore": payload["pro_score"],
                "ConScore": payload["con_score"],
                "Confidence": f"{payload['confidence']:.4f}",
                "RawResponse": raw_response,
                "RecordedAtUtc": datetime.now(timezone.utc).isoformat(),
            },
        )
        added += 1
        print(
            f"completed annotator={args.annotator} debate={record['debate_id']} "
            f"added={added}/{len(remaining)}",
            flush=True,
        )
        if args.max_new_calls and added >= args.max_new_calls:
            break
        if args.call_delay:
            time.sleep(args.call_delay)


if __name__ == "__main__":
    main()
