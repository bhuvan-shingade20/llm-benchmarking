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
from run_generated_forced_choice import call_with_retries


FIELDS = [
    "ProtocolVersion",
    "ComparisonId",
    "TopicId",
    "DebateId1",
    "DebateId2",
    "FixedOpponent",
    "TestedPosition",
    "CandidateStarts",
    "Candidate1Model",
    "Candidate2Model",
    "JudgeSpec",
    "JudgeDisplayName",
    "JudgeProvider",
    "WinnerModel",
    "WinnerCandidate",
    "PromptSha256",
    "RawResponse",
    "RecordedAtUtc",
]

MANIFEST_FIELDS = FIELDS[:10]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Forced-choice matched same-position judging with a fixed opponent."
    )
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--judge", required=True)
    parser.add_argument("--call-delay", type=float, default=10.0)
    parser.add_argument("--rate-limit-sleep", type=int, default=600)
    parser.add_argument("--max-new-calls", type=int)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def model_position(row: dict[str, str], model: str) -> str:
    if row["Model1name"] == model:
        return row["Model1Position"]
    if row["Model2name"] == model:
        return row["Model2Position"]
    raise ValueError(f"Model {model!r} is absent from debate {row['DebateId']}")


def model_starts(row: dict[str, str], model: str) -> bool:
    slot = "Model1" if row["Model1name"] == model else "Model2"
    return row["starting"] == slot


def topic_lookup(path: Path) -> dict[tuple[str, str], dict[str, object]]:
    topics = json.loads(path.read_text(encoding="utf-8"))
    lookup = {
        (str(topic["position_a"]).strip(), str(topic["position_b"]).strip()): topic
        for topic in topics
    }
    if len(lookup) != len(topics):
        raise ValueError("Topic position pairs must be unique")
    return lookup


def build_comparisons(
    raw_rows: list[dict[str, str]], config: dict[str, object]
) -> list[dict[str, str]]:
    expected_debates = int(config["generated_debates"]["expected_debates"])
    if len(raw_rows) != expected_debates:
        raise ValueError(f"Expected {expected_debates} raw debates, found {len(raw_rows)}")

    topics_path = Path(config["generated_debates"]["topics_file"])
    topics = topic_lookup(topics_path)
    configured_models = sorted(
        parse_model_spec(model["spec"], "openai").model for model in config["models"]
    )
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    topic_meta: dict[str, dict[str, object]] = {}
    for row in raw_rows:
        key = (row["positionA"].strip(), row["positionB"].strip())
        if key not in topics:
            raise ValueError(f"Unknown position pair in debate {row['DebateId']}")
        topic = topics[key]
        topic_id = str(topic["id"])
        grouped[topic_id].append(row)
        topic_meta[topic_id] = topic

    expected_per_topic = len(configured_models) * (len(configured_models) - 1) // 2 * 4
    index = {}
    for topic_id, rows in grouped.items():
        if len(rows) != expected_per_topic:
            raise ValueError(
                f"Topic {topic_id} has {len(rows)} debates; expected {expected_per_topic}"
            )
        for row in rows:
            pair = frozenset((row["Model1name"], row["Model2name"]))
            for candidate in pair:
                key = (
                    topic_id,
                    pair,
                    candidate,
                    model_position(row, candidate),
                    model_starts(row, candidate),
                )
                if key in index:
                    raise ValueError(f"Duplicate same-position source condition: {key}")
                index[key] = row

    seed = str(config["same_position"]["opponent_assignment_seed"])
    tasks = []
    for topic_index, topic_id in enumerate(sorted(grouped)):
        for pair_index, pair_tuple in enumerate(combinations(configured_models, 2)):
            for position_index, tested_position in enumerate(("A", "B")):
                for start_index, candidate_starts in enumerate((False, True)):
                    tasks.append(
                        (topic_index, topic_id, pair_index, pair_tuple, position_index, tested_position, start_index, candidate_starts)
                    )
    opponent_counts = Counter()
    candidate_opponent_counts = Counter()
    opponent_by_condition = {}
    for task in sorted(
        tasks,
        key=lambda item: hashlib.sha256(
            f"{seed}|{item[1]}|{item[2]}|{item[5]}|{item[7]}".encode()
        ).hexdigest(),
    ):
        _, topic_id, pair_index, pair_tuple, _, tested_position, _, candidate_starts = task
        remaining = [model for model in configured_models if model not in pair_tuple]
        opponent = min(
            remaining,
            key=lambda model: (
                opponent_counts[model],
                sum(candidate_opponent_counts[(candidate, model)] for candidate in pair_tuple),
                hashlib.sha256(
                    f"{seed}|{topic_id}|{pair_index}|{tested_position}|{candidate_starts}|{model}".encode()
                ).hexdigest(),
            ),
        )
        opponent_by_condition[(topic_id, pair_index, tested_position, candidate_starts)] = opponent
        opponent_counts[opponent] += 1
        for candidate in pair_tuple:
            candidate_opponent_counts[(candidate, opponent)] += 1

    task_by_condition = {
        (task[1], task[2], task[5], task[7]): task for task in tasks
    }
    while max(opponent_counts.values()) - min(opponent_counts.values()) > 1:
        high = max(configured_models, key=lambda model: (opponent_counts[model], model))
        low = min(configured_models, key=lambda model: (opponent_counts[model], model))
        eligible = []
        for key, assigned in opponent_by_condition.items():
            task = task_by_condition[key]
            pair_tuple = task[3]
            if assigned == high and low not in pair_tuple:
                imbalance_cost = sum(
                    candidate_opponent_counts[(candidate, low)]
                    - candidate_opponent_counts[(candidate, high)]
                    for candidate in pair_tuple
                )
                eligible.append((imbalance_cost, key, pair_tuple))
        if not eligible:
            raise ValueError("Could not balance fixed-opponent exposure")
        _, key, pair_tuple = min(eligible)
        opponent_by_condition[key] = low
        opponent_counts[high] -= 1
        opponent_counts[low] += 1
        for candidate in pair_tuple:
            candidate_opponent_counts[(candidate, high)] -= 1
            candidate_opponent_counts[(candidate, low)] += 1

    comparisons_out = []
    comparison_id = 1
    for topic_index, topic_id in enumerate(sorted(grouped)):
        for pair_index, pair_tuple in enumerate(combinations(configured_models, 2)):
            for position_index, tested_position in enumerate(("A", "B")):
                for start_index, candidate_starts in enumerate((False, True)):
                    opponent = opponent_by_condition[
                        (topic_id, pair_index, tested_position, candidate_starts)
                    ]
                    left, right = pair_tuple
                    row_left = index[
                        (topic_id, frozenset((left, opponent)), left, tested_position, candidate_starts)
                    ]
                    row_right = index[
                        (topic_id, frozenset((right, opponent)), right, tested_position, candidate_starts)
                    ]
                    if (topic_index + pair_index + position_index + start_index) % 2:
                        candidate1, candidate2 = right, left
                        row1, row2 = row_right, row_left
                    else:
                        candidate1, candidate2 = left, right
                        row1, row2 = row_left, row_right
                    comparisons_out.append(
                        {
                            "ProtocolVersion": str(config["protocol_version"]),
                            "ComparisonId": str(comparison_id),
                            "TopicId": topic_id,
                            "DebateId1": row1["DebateId"],
                            "DebateId2": row2["DebateId"],
                            "FixedOpponent": opponent,
                            "TestedPosition": tested_position,
                            "CandidateStarts": "yes" if candidate_starts else "no",
                            "Candidate1Model": candidate1,
                            "Candidate2Model": candidate2,
                        }
                    )
                    comparison_id += 1

    expected = int(config["same_position"]["expected_comparisons"])
    if len(comparisons_out) != expected:
        raise ValueError(f"Expected {expected} comparisons, found {len(comparisons_out)}")
    candidate_counts = Counter()
    order_counts = Counter()
    for row in comparisons_out:
        candidate_counts.update((row["Candidate1Model"], row["Candidate2Model"]))
        order_counts.update((row["Candidate1Model"],))
        if row["FixedOpponent"] in {row["Candidate1Model"], row["Candidate2Model"]}:
            raise ValueError("Fixed opponent cannot be one of the compared candidates")
    if len(set(candidate_counts.values())) != 1:
        raise ValueError(f"Candidate exposure is not balanced: {candidate_counts}")
    if max(order_counts.values()) - min(order_counts.values()) > 1:
        raise ValueError(f"Candidate presentation is not balanced: {order_counts}")
    fixed_opponent_counts = Counter(row["FixedOpponent"] for row in comparisons_out)
    if max(fixed_opponent_counts.values()) - min(fixed_opponent_counts.values()) > 1:
        raise ValueError(f"Fixed-opponent exposure is not balanced: {fixed_opponent_counts}")
    return comparisons_out


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def read_existing(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            raise ValueError(f"Unexpected columns in {path}: {reader.fieldnames}")
        rows = list(reader)
    if len(rows) != len({row["ComparisonId"] for row in rows}):
        raise ValueError(f"Duplicate comparison ids in {path}")
    return rows


def append_row(path: Path, row: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(row)
        handle.flush()


def transcript_excerpt(row: dict[str, str], candidate: str, max_words: int = 55) -> str:
    candidate_slot = "Model1" if row["Model1name"] == candidate else "Model2"
    opponent_slot = "Model2" if candidate_slot == "Model1" else "Model1"
    blocks = []
    for block in row["DiscussionPlainText"].split("\n\n"):
        match = re.match(r"^(Model[12]):\s*(.*)$", block.strip(), flags=re.DOTALL)
        if not match:
            continue
        speaker, content = match.groups()
        words = content.split()
        suffix = " [...]" if len(words) > max_words else ""
        label = "Candidate" if speaker == candidate_slot else "Fixed opponent"
        if speaker not in {candidate_slot, opponent_slot}:
            raise ValueError(f"Unexpected speaker label {speaker!r}")
        blocks.append(f"{label}: {' '.join(words[:max_words])}{suffix}")
    if len(blocks) != 8:
        raise ValueError(f"Expected eight transcript turns, found {len(blocks)}")
    return "\n\n".join(blocks)


def prompts(
    comparison: dict[str, str], raw_by_id: dict[str, dict[str, str]]
) -> tuple[str, str]:
    row1 = raw_by_id[comparison["DebateId1"]]
    row2 = raw_by_id[comparison["DebateId2"]]
    position = (
        row1["positionA"]
        if comparison["TestedPosition"] == "A"
        else row1["positionB"]
    )
    system = (
        "You are an impartial debate evaluator. Compare two candidates defending the "
        "same proposition against the same opposing model under matched speaking "
        "conditions. Decide which candidate made the stronger case using argument "
        "quality, responsiveness, factual discipline, and persuasive clarity. Ignore "
        "your own policy preference. You must select one candidate; ties are not allowed."
    )
    user = f"""
Tested proposition:
{position}

Both candidates debate against the same fixed opponent: {comparison['FixedOpponent']}.
Both candidates have the same starting status: {comparison['CandidateStarts']}.

Candidate 1 is {comparison['Candidate1Model']}.
Candidate 1 debate:
{transcript_excerpt(row1, comparison['Candidate1Model'])}

Candidate 2 is {comparison['Candidate2Model']}.
Candidate 2 debate:
{transcript_excerpt(row2, comparison['Candidate2Model'])}

Which candidate defended the tested proposition better?
Candidate 1 is option 1. Candidate 2 is option 2.
Reply with exactly one digit: 1 or 2. Your entire reply must be one character.
""".strip()
    return system, user


def main() -> None:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    model_meta = {model["spec"]: model for model in config["models"]}
    if args.judge not in model_meta:
        raise ValueError(f"Judge {args.judge!r} is not in the configured panel")
    raw_rows = read_raw_rows(args.raw)
    comparisons = build_comparisons(raw_rows, config)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_manifest(args.output_dir / "same_position_manifest.csv", comparisons)

    output = args.output_dir / f"judgements_{slug(args.judge)}.csv"
    existing = read_existing(output)
    completed = {row["ComparisonId"] for row in existing}
    remaining = [row for row in comparisons if row["ComparisonId"] not in completed]
    print(
        f"judge={args.judge} planned={len(comparisons)} existing={len(existing)} "
        f"remaining={len(remaining)}",
        flush=True,
    )
    if args.dry_run:
        return

    raw_by_id = {row["DebateId"]: row for row in raw_rows}
    spec = parse_model_spec(args.judge, "openai")
    client = build_client(spec.provider)
    added = 0
    for comparison in remaining:
        system, user = prompts(comparison, raw_by_id)
        winner_candidate, raw_response = call_with_retries(
            client, spec.model, system, user, args.rate_limit_sleep
        )
        winner_model = (
            comparison["Candidate1Model"]
            if winner_candidate == "Candidate 1"
            else comparison["Candidate2Model"]
        )
        append_row(
            output,
            {
                **comparison,
                "JudgeSpec": args.judge,
                "JudgeDisplayName": model_meta[args.judge]["display_name"],
                "JudgeProvider": spec.provider,
                "WinnerModel": winner_model,
                "WinnerCandidate": winner_candidate,
                "PromptSha256": hashlib.sha256(
                    f"{system}\n\n{user}".encode("utf-8")
                ).hexdigest(),
                "RawResponse": raw_response,
                "RecordedAtUtc": datetime.now(timezone.utc).isoformat(),
            },
        )
        added += 1
        print(
            f"completed judge={args.judge} comparison={comparison['ComparisonId']} "
            f"added={added}/{len(remaining)}",
            flush=True,
        )
        if args.max_new_calls and added >= args.max_new_calls:
            break
        if args.call_delay and spec.provider == "openai":
            time.sleep(args.call_delay)


if __name__ == "__main__":
    main()
