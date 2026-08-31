import argparse
import csv
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from generate_judgement_files import (
    DEFAULT_JUDGES,
    call_judge,
    confidence_value,
    diff_prompt,
    normalize_winner,
    read_raw_rows,
)


DEFAULT_RAW = Path("data/paper_dataset/RawDebates.csv")
DEFAULT_ORIGINAL = Path("data/paper_dataset/judgements/DiffPosJudgements.csv")
DEFAULT_TOPICS = Path("topics/phase1_topics.json")
DEFAULT_OUTPUT_DIR = Path("runs/2026-08-28_repeated_judgment_stability")

OUTPUT_FIELDS = [
    "DebateId",
    "TopicId",
    "Model1name",
    "Model2name",
    "Model1Position",
    "starting",
    "Judge",
    "RepeatIndex",
    "Winner",
    "Confidence",
    "PromptSha256",
    "Temperature",
    "MaxTokens",
    "Source",
    "RecordedAtUtc",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Repeat cloud judgments on fixed debate transcripts for stability analysis."
    )
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--original", type=Path, default=DEFAULT_ORIGINAL)
    parser.add_argument("--topics", type=Path, default=DEFAULT_TOPICS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--judge", choices=DEFAULT_JUDGES, required=True)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--call-delay", type=float, default=10.0)
    parser.add_argument("--rate-limit-sleep", type=int, default=600)
    parser.add_argument("--max-new-calls", type=int)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def load_topic_lookup(path: Path) -> dict[tuple[str, str], str]:
    topics = json.loads(path.read_text(encoding="utf-8"))
    return {
        (topic["position_a"].strip(), topic["position_b"].strip()): topic["id"]
        for topic in topics
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def read_existing(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != OUTPUT_FIELDS:
            raise ValueError(f"Unexpected columns in {path}: {reader.fieldnames}")
        rows = list(reader)
    keys = [(row["DebateId"], row["Judge"], row["RepeatIndex"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError(f"Duplicate judgment keys in {path}")
    return rows


def append_row(path: Path, row: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(row)
        handle.flush()


def append_error(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        handle.flush()


def original_columns(fieldnames: list[str], judge: str) -> tuple[str, str]:
    winner_suffix = f"({judge}) winner"
    confidence_suffix = f"({judge}) confidence"
    winners = [field for field in fieldnames if field.endswith(winner_suffix)]
    confidences = [field for field in fieldnames if field.endswith(confidence_suffix)]
    if len(winners) != 1 or len(confidences) != 1:
        raise ValueError(f"Could not identify original columns for {judge}")
    return winners[0], confidences[0]


def prompt_sha256(system_prompt: str, user_prompt: str) -> str:
    return hashlib.sha256(f"{system_prompt}\n\n{user_prompt}".encode("utf-8")).hexdigest()


def base_row(
    raw: dict[str, str],
    topic_id: str,
    judge: str,
    repeat_index: int,
    winner: str,
    confidence: str,
    prompt_hash: str,
    source: str,
    recorded_at: str,
) -> dict[str, str]:
    return {
        "DebateId": raw["DebateId"],
        "TopicId": topic_id,
        "Model1name": raw["Model1name"],
        "Model2name": raw["Model2name"],
        "Model1Position": raw["Model1Position"],
        "starting": raw["starting"],
        "Judge": judge,
        "RepeatIndex": str(repeat_index),
        "Winner": winner,
        "Confidence": confidence,
        "PromptSha256": prompt_hash,
        "Temperature": "0.1",
        "MaxTokens": "220",
        "Source": source,
        "RecordedAtUtc": recorded_at,
    }


def main() -> None:
    args = parse_args()
    if args.repeats < 2:
        raise ValueError("--repeats must be at least 2")

    raw_rows = read_raw_rows(args.raw)
    if len(raw_rows) != 240:
        raise ValueError(f"Expected 240 raw debates, found {len(raw_rows)}")
    original_rows = read_csv(args.original)
    if len(original_rows) != 240:
        raise ValueError(f"Expected 240 original judgments, found {len(original_rows)}")
    original_by_id = {row["DebateId"]: row for row in original_rows}
    winner_column, confidence_column = original_columns(list(original_rows[0]), args.judge)
    topic_lookup = load_topic_lookup(args.topics)

    output_path = args.output_dir / f"judgements_{slug(args.judge)}.csv"
    error_path = args.output_dir / f"errors_{slug(args.judge)}.jsonl"
    existing_rows = read_existing(output_path)
    completed = {
        (row["DebateId"], row["Judge"], int(row["RepeatIndex"]))
        for row in existing_rows
    }

    planned_new = sum(
        (raw["DebateId"], args.judge, repeat_index) not in completed
        for raw in raw_rows
        for repeat_index in range(2, args.repeats + 1)
    )
    print(
        f"judge={args.judge} debates={len(raw_rows)} repeats={args.repeats} "
        f"existing={len(existing_rows)} new_api_calls={planned_new}",
        flush=True,
    )
    if args.dry_run:
        return

    for raw in raw_rows:
        key = (raw["positionA"].strip(), raw["positionB"].strip())
        if key not in topic_lookup:
            raise ValueError(f"Could not map debate {raw['DebateId']} to a topic")
        original = original_by_id[raw["DebateId"]]
        system_prompt, user_prompt = diff_prompt(raw)
        prompt_hash = prompt_sha256(system_prompt, user_prompt)
        repeat_one_key = (raw["DebateId"], args.judge, 1)
        if repeat_one_key not in completed:
            append_row(
                output_path,
                base_row(
                    raw,
                    topic_lookup[key],
                    args.judge,
                    1,
                    original[winner_column],
                    original[confidence_column],
                    prompt_hash,
                    "original_curated_judgment",
                    "",
                ),
            )
            completed.add(repeat_one_key)

    new_calls = 0
    failures = 0
    for raw in raw_rows:
        topic_id = topic_lookup[(raw["positionA"].strip(), raw["positionB"].strip())]
        system_prompt, user_prompt = diff_prompt(raw)
        prompt_hash = prompt_sha256(system_prompt, user_prompt)
        allowed = [raw["Model1name"], raw["Model2name"], "Tie"]
        for repeat_index in range(2, args.repeats + 1):
            key = (raw["DebateId"], args.judge, repeat_index)
            if key in completed:
                continue
            try:
                result = call_judge(
                    args.judge,
                    system_prompt,
                    user_prompt,
                    args.rate_limit_sleep,
                )
                winner = normalize_winner(result.get("winner"), allowed)
                append_row(
                    output_path,
                    base_row(
                        raw,
                        topic_id,
                        args.judge,
                        repeat_index,
                        winner,
                        confidence_value(result.get("confidence")),
                        prompt_hash,
                        "cloud_repeat",
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                completed.add(key)
                new_calls += 1
                print(
                    f"completed judge={args.judge} debate={raw['DebateId']} "
                    f"repeat={repeat_index} new_calls={new_calls}/{planned_new}",
                    flush=True,
                )
                if args.call_delay:
                    time.sleep(args.call_delay)
            except Exception as error:
                failures += 1
                append_error(
                    error_path,
                    {
                        "DebateId": raw["DebateId"],
                        "Judge": args.judge,
                        "RepeatIndex": repeat_index,
                        "RecordedAtUtc": datetime.now(timezone.utc).isoformat(),
                        "Error": str(error),
                    },
                )
                print(
                    f"failed judge={args.judge} debate={raw['DebateId']} "
                    f"repeat={repeat_index}: {error}",
                    flush=True,
                )
            if args.max_new_calls and new_calls >= args.max_new_calls:
                print(f"Stopped after {new_calls} new calls; failures={failures}", flush=True)
                return

    expected = len(raw_rows) * args.repeats
    final_rows = read_existing(output_path)
    print(
        f"finished judge={args.judge} rows={len(final_rows)}/{expected} "
        f"new_calls={new_calls} failures={failures}",
        flush=True,
    )


if __name__ == "__main__":
    main()
