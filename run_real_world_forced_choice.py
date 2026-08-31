import argparse
import csv
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from run_conversation import build_client, complete_chat, parse_model_spec


DEFAULT_INPUT = Path("data/external/poliprop/PoliPropPrepared.jsonl")
DEFAULT_CONFIG = Path("configs/extension_2026_08_29.json")
DEFAULT_OUTPUT_DIR = Path("runs/2026-08-29_real_world_forced_choice_v2")

FIELDS = [
    "ProtocolVersion",
    "DebateId",
    "JudgeSpec",
    "JudgeDisplayName",
    "JudgeProvider",
    "PromptVersion",
    "PresentationOrder",
    "RepeatIndex",
    "WinnerSide",
    "WinnerCandidate",
    "HumanMajority",
    "HumanAgreement",
    "RobustnessSample",
    "PromptSha256",
    "RawResponse",
    "RecordedAtUtc",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run forced-choice LLM judgments on the real-world PoliProp debates."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--judge", required=True, help="Exact provider:model spec from the config.")
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


def load_config(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def judge_metadata(config: dict[str, object], judge_spec: str) -> dict[str, str]:
    for model in config["models"]:
        if model["spec"] == judge_spec:
            return model
    raise ValueError(f"Judge {judge_spec!r} is not in the frozen six-model panel.")


def planned_conditions(record: dict[str, object]) -> list[tuple[str, str, int]]:
    conditions = [("canonical", "pro_first", 1)]
    if record["robustness_sample"]:
        conditions.extend(
            [
                ("canonical", "pro_first", 2),
                ("canonical", "pro_first", 3),
                ("canonical", "con_first", 1),
                ("paraphrase", "pro_first", 1),
            ]
        )
    return conditions


def prompts(
    record: dict[str, object], prompt_version: str, presentation_order: str
) -> tuple[str, str, dict[str, str]]:
    if prompt_version == "canonical":
        system_prompt = (
            "You are an impartial debate evaluator. Decide which candidate made the more "
            "convincing case using argument quality, responsiveness, factual discipline, and "
            "persuasive clarity. Ignore your own policy preference. You must select one "
            "candidate; ties are not allowed."
        )
        question = "Which candidate made the more convincing case?"
    elif prompt_version == "paraphrase":
        system_prompt = (
            "Act as a neutral adjudicator. Compare the two cases for reasoning, engagement, "
            "factual care, and clarity rather than whether you personally support either view. "
            "Return the stronger candidate even when the difference is small; do not return a tie."
        )
        question = "Which candidate presented the stronger overall argument?"
    else:
        raise ValueError(f"Unknown prompt version: {prompt_version}")

    side_to_excerpt = {
        "Pro": str(record["pro_excerpt"]),
        "Con": str(record["con_excerpt"]),
    }
    candidate_to_side = (
        {"Candidate 1": "Pro", "Candidate 2": "Con"}
        if presentation_order == "pro_first"
        else {"Candidate 1": "Con", "Candidate 2": "Pro"}
    )
    candidate_blocks = []
    for candidate in ("Candidate 1", "Candidate 2"):
        side = candidate_to_side[candidate]
        candidate_blocks.append(
            f"{candidate} ({side} side):\n{side_to_excerpt[side]}"
        )
    user_prompt = f"""
Proposition:
{record['proposition']}

{candidate_blocks[0]}

{candidate_blocks[1]}

{question}
Candidate 1 is option 1. Candidate 2 is option 2.
Reply with exactly one digit: 1 or 2. Your entire reply must be one character.
""".strip()
    return system_prompt, user_prompt, candidate_to_side


def parse_winner(value: str) -> str:
    cleaned = value.strip().strip("`").strip()
    try:
        payload = json.loads(cleaned)
        if isinstance(payload, dict):
            cleaned = str(payload.get("winner", payload.get("answer", "")))
    except json.JSONDecodeError:
        pass
    matches = re.findall(
        r"(?:candidate|option)\s*([12])", cleaned, flags=re.IGNORECASE
    )
    unique = set(matches)
    if len(unique) == 1:
        return f"Candidate {next(iter(unique))}"
    if cleaned.lower() in {"1", "candidate one"}:
        return "Candidate 1"
    if cleaned.lower() in {"2", "candidate two"}:
        return "Candidate 2"
    raise ValueError(f"Could not extract one forced-choice candidate from {value!r}")


def call_with_retries(
    client,
    model: str,
    system_prompt: str,
    user_prompt: str,
    rate_limit_sleep: int,
) -> tuple[str, str]:
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
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.1,
                response_format=response_format,
            )
            return parse_winner(response), response
        except Exception as error:
            last_error = error
            lowered = str(error).lower()
            wait_seconds = (
                rate_limit_sleep
                if "429" in lowered or "rate limit" in lowered
                else min(45 * attempt, 180)
            )
            print(
                f"attempt={attempt} failed: {error}; retrying in {wait_seconds}s",
                flush=True,
            )
            time.sleep(wait_seconds)
    raise RuntimeError(f"Forced-choice judgment failed after retries: {last_error}")


def read_existing(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            raise ValueError(f"Unexpected columns in {path}: {reader.fieldnames}")
        rows = list(reader)
    keys = [
        (
            row["DebateId"],
            row["JudgeSpec"],
            row["PromptVersion"],
            row["PresentationOrder"],
            row["RepeatIndex"],
        )
        for row in rows
    ]
    if len(keys) != len(set(keys)):
        raise ValueError(f"Duplicate result keys in {path}")
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
    config = load_config(args.config)
    meta = judge_metadata(config, args.judge)
    spec = parse_model_spec(args.judge, "openai")
    records = [record for record in read_jsonl(args.input) if record["primary_eligible"]]
    if len(records) != 740:
        raise ValueError(f"Expected 740 decisive human debates, found {len(records)}")
    if sum(bool(record["robustness_sample"]) for record in records) != 120:
        raise ValueError("Expected a 120-debate robustness sample.")

    output = args.output_dir / f"judgements_{slug(args.judge)}.csv"
    existing_rows = read_existing(output)
    completed = {
        (
            int(row["DebateId"]),
            row["PromptVersion"],
            row["PresentationOrder"],
            int(row["RepeatIndex"]),
        )
        for row in existing_rows
    }
    planned = [
        (record, prompt_version, order, repeat_index)
        for record in records
        for prompt_version, order, repeat_index in planned_conditions(record)
    ]
    remaining = [
        item
        for item in planned
        if (
            int(item[0]["debate_id"]),
            item[1],
            item[2],
            item[3],
        )
        not in completed
    ]
    print(
        f"judge={args.judge} planned={len(planned)} existing={len(existing_rows)} "
        f"remaining={len(remaining)}",
        flush=True,
    )
    if len(planned) != 1220:
        raise ValueError(f"Expected 1,220 conditions per judge, found {len(planned)}")
    if args.dry_run:
        return

    client = build_client(spec.provider)
    added = 0
    for record, prompt_version, order, repeat_index in remaining:
        system_prompt, user_prompt, candidate_to_side = prompts(
            record, prompt_version, order
        )
        winner_candidate, raw_response = call_with_retries(
            client,
            spec.model,
            system_prompt,
            user_prompt,
            args.rate_limit_sleep,
        )
        winner_side = candidate_to_side[winner_candidate]
        prompt_hash = hashlib.sha256(
            f"{system_prompt}\n\n{user_prompt}".encode("utf-8")
        ).hexdigest()
        append_row(
            output,
            {
                "ProtocolVersion": config["protocol_version"],
                "DebateId": record["debate_id"],
                "JudgeSpec": args.judge,
                "JudgeDisplayName": meta["display_name"],
                "JudgeProvider": spec.provider,
                "PromptVersion": prompt_version,
                "PresentationOrder": order,
                "RepeatIndex": repeat_index,
                "WinnerSide": winner_side,
                "WinnerCandidate": winner_candidate,
                "HumanMajority": record["human_majority"],
                "HumanAgreement": int(winner_side == record["human_majority"]),
                "RobustnessSample": int(bool(record["robustness_sample"])),
                "PromptSha256": prompt_hash,
                "RawResponse": raw_response,
                "RecordedAtUtc": datetime.now(timezone.utc).isoformat(),
            },
        )
        added += 1
        print(
            f"completed judge={args.judge} debate={record['debate_id']} "
            f"condition={prompt_version}/{order}/r{repeat_index} "
            f"added={added}/{len(remaining)}",
            flush=True,
        )
        if args.max_new_calls and added >= args.max_new_calls:
            break
        if args.call_delay and spec.provider == "openai":
            time.sleep(args.call_delay)


if __name__ == "__main__":
    main()
