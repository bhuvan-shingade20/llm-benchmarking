import argparse
import csv
import hashlib
import json
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

from generate_judgement_files import read_raw_rows
from run_conversation import build_client, parse_model_spec
from run_generated_forced_choice import call_with_retries, prompts, transcript_excerpt


CONFIG = Path("configs/experiment_2_robustness_2026_09_03.json")
PANEL_CONFIG = Path("configs/experiment_1_replication_2026_09_03.json")
SOURCE_DIR = Path("runs/2026-09-03_exp1_replication")
OUTPUT_DIR = Path("runs/2026-09-03_exp2_robustness")
FIELDS = [
    "ProtocolVersion",
    "DebateId",
    "TopicId",
    "JudgeSpec",
    "Condition",
    "PresentationOrder",
    "WinnerModel",
    "WinnerCandidate",
    "PromptSha256",
    "RawResponse",
    "RecordedAtUtc",
    "Source",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the frozen prompt/order robustness study.")
    parser.add_argument("--judge", required=True)
    parser.add_argument("--call-delay", type=float, default=10.0)
    parser.add_argument("--rate-limit-sleep", type=int, default=600)
    parser.add_argument("--max-new-calls", type=int)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def append_row(path: Path, row: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(row)
        handle.flush()


def topic_map(panel: dict[str, object]) -> tuple[dict[tuple[str, str], str], set[str]]:
    topics = json.loads(Path(panel["generated_debates"]["topics_file"]).read_text(encoding="utf-8"))
    mapping = {(topic["position_a"], topic["position_b"]): topic["id"] for topic in topics}
    original = {topic["id"] for topic in topics if "expected_easier_position" not in topic}
    return mapping, original


def sample_rows(rows: list[dict[str, str]], config: dict[str, object], panel: dict[str, object]) -> list[dict[str, str]]:
    mapping, original_ids = topic_map(panel)
    grouped: dict[str, list[dict[str, str]]] = {topic_id: [] for topic_id in original_ids}
    for row in rows:
        topic_id = mapping[(row["positionA"], row["positionB"])]
        if topic_id in grouped:
            grouped[topic_id].append(row)
    per_topic = int(config["sample_size"]) // len(grouped)
    if per_topic != 12 or per_topic * len(grouped) != int(config["sample_size"]):
        raise ValueError("Robustness sample size must divide evenly across original topics")
    selected = []
    for topic_id in sorted(grouped):
        by_pair = defaultdict(list)
        for row in grouped[topic_id]:
            by_pair[tuple(sorted((row["Model1name"], row["Model2name"])))].append(row)
        pair_sets = []
        for pair_set in combinations(sorted(by_pair), 6):
            degree = Counter(model for pair in pair_set for model in pair)
            if len(degree) == 6 and set(degree.values()) == {2}:
                digest = hashlib.sha256(
                    f"{config['sample_seed']}|{topic_id}|{pair_set}".encode()
                ).hexdigest()
                pair_sets.append((digest, pair_set))
        if not pair_sets:
            raise ValueError(f"Could not construct a balanced sample for topic {topic_id}")
        _, chosen_pairs = min(pair_sets)
        chosen_rows = []
        for pair in chosen_pairs:
            pair_rows = by_pair[pair]
            if len(pair_rows) != 4:
                raise ValueError(f"Topic {topic_id}, pair {pair} has {len(pair_rows)} conditions")
            parity = int(
                hashlib.sha256(f"{config['sample_seed']}|{topic_id}|{pair}".encode()).hexdigest(),
                16,
            ) % 2
            chosen_rows.extend(
                row
                for row in pair_rows
                if ((row["Model1Position"] == "A") == (row["starting"] == "Model1"))
                == (parity == 0)
            )
        if len(chosen_rows) != per_topic:
            raise ValueError(f"Balanced sample for topic {topic_id} has {len(chosen_rows)} rows")
        for row in chosen_rows:
            row = dict(row)
            row["TopicId"] = topic_id
            selected.append(row)
    if len(selected) != int(config["sample_size"]):
        raise ValueError("Robustness sample validation failed")
    return sorted(selected, key=lambda row: int(row["DebateId"]))


def transformed_prompts(
    row: dict[str, str], messages: list[dict[str, str]], condition: str
) -> tuple[str, str, str, str]:
    system, user, _ = prompts(row, messages)
    candidate1, candidate2 = row["Model1name"], row["Model2name"]
    order = "canonical"
    if condition == "reversed":
        candidate1, candidate2 = candidate2, candidate1
        order = "reversed"
        excerpt, _ = transcript_excerpt(messages, row["Model1Position"])
        excerpt = excerpt.replace("Model1:", "__FIRST_MODEL__:")
        excerpt = excerpt.replace("Model2:", "Candidate 1:")
        excerpt = excerpt.replace("__FIRST_MODEL__:", "Candidate 2:")
        system = (
            "You are an impartial debate evaluator. Decide which model argued its assigned "
            "position more convincingly using argument quality, responsiveness, factual "
            "discipline, and persuasive clarity. Ignore your own policy preference. You must "
            "select one model; ties are not allowed."
        )
        user = f"""
Position A:
{row['positionA']}

Position B:
{row['positionB']}

Candidate 1 is {candidate1}. Candidate 2 is {candidate2}.

Transcript:
{excerpt}

Which candidate argued its assigned position better?
Candidate 1 is option 1. Candidate 2 is option 2.
Reply with exactly one digit: 1 or 2. Your entire reply must be one character.
""".strip()
    elif condition == "paraphrased":
        system = (
            "Act as a neutral adjudicator. Compare the two debaters for sound reasoning, direct "
            "engagement, factual care, and persuasive clarity, regardless of which position you "
            "personally prefer. Choose the stronger debater even when the difference is small. "
            "A tie is not permitted."
        )
        user = user.replace(
            "Which candidate argued its assigned position better?",
            "Considering the full exchange, which candidate presented the stronger case?",
        )
    return system, user, candidate1, candidate2


def main() -> None:
    args = parse_args()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    panel = json.loads(PANEL_CONFIG.read_text(encoding="utf-8"))
    model_specs = {model["spec"] for model in panel["models"]}
    if args.judge not in model_specs:
        raise ValueError("Judge is not in the shared debater/judge panel")
    raw_rows = read_raw_rows(SOURCE_DIR / "RawDebates.csv")
    if len(raw_rows) != int(panel["generated_debates"]["expected_debates"]):
        raise ValueError("Experiment 1 must be complete before Experiment 2 starts")
    selected = sample_rows(raw_rows, config, panel)
    base_path = SOURCE_DIR / "different_position" / f"judgements_{slug(args.judge)}.csv"
    base = {row["DebateId"]: row for row in read_csv(base_path)}
    if len(base) != len(raw_rows):
        raise ValueError("The canonical Experiment 1 judge stream must be complete")

    output = OUTPUT_DIR / f"judgements_{slug(args.judge)}.csv"
    existing = read_csv(output)
    completed = {(row["DebateId"], row["Condition"]) for row in existing}
    conditions = ("canonical_1", "canonical_2", "canonical_3", "reversed", "paraphrased")
    planned = [(row, condition) for row in selected for condition in conditions]
    remaining = [(row, condition) for row, condition in planned if (row["DebateId"], condition) not in completed]
    print(f"judge={args.judge} planned={len(planned)} existing={len(existing)} remaining={len(remaining)}", flush=True)
    if args.dry_run:
        return

    spec = parse_model_spec(args.judge, "openai")
    client = build_client(spec.provider)
    added = 0
    for row, condition in remaining:
        if condition == "canonical_1":
            source = base[row["DebateId"]]
            winner_model = source["WinnerModel"]
            winner_candidate = source["WinnerCandidate"]
            prompt_hash = source["PromptSha256"]
            raw_response = source["RawResponse"]
            source_label = "experiment_1_reuse"
            presentation_order = "canonical"
        else:
            transcript_path = SOURCE_DIR / "transcripts" / f"debate_{int(row['DebateId']):04d}.json"
            messages = json.loads(transcript_path.read_text(encoding="utf-8"))
            system, user, candidate1, candidate2 = transformed_prompts(row, messages, condition)
            winner_candidate, raw_response = call_with_retries(
                client, spec.model, system, user, args.rate_limit_sleep
            )
            winner_model = candidate1 if winner_candidate == "Candidate 1" else candidate2
            prompt_hash = hashlib.sha256(f"{system}\n\n{user}".encode()).hexdigest()
            source_label = "new_judgment"
            presentation_order = "reversed" if condition == "reversed" else "canonical"
        append_row(
            output,
            {
                "ProtocolVersion": config["protocol_version"],
                "DebateId": row["DebateId"],
                "TopicId": row["TopicId"],
                "JudgeSpec": args.judge,
                "Condition": condition,
                "PresentationOrder": presentation_order,
                "WinnerModel": winner_model,
                "WinnerCandidate": winner_candidate,
                "PromptSha256": prompt_hash,
                "RawResponse": raw_response,
                "RecordedAtUtc": datetime.now(timezone.utc).isoformat(),
                "Source": source_label,
            },
        )
        added += 1
        if args.max_new_calls and added >= args.max_new_calls:
            break
        if condition != "canonical_1" and args.call_delay and spec.provider == "openai":
            time.sleep(args.call_delay)


if __name__ == "__main__":
    main()
