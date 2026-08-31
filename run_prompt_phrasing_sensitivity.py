import argparse
import csv
import hashlib
import json
import time
from collections import Counter
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
DEFAULT_TOPICS = Path("topics/phase1_topics.json")
DEFAULT_OUTPUT_DIR = Path("runs/prompt_phrasing_sensitivity")

PROMPT_VARIANTS = {
    "canonical": """
You are an impartial debate judge.
Select which model argued its assigned position better in this debate.
Judge argument quality, responsiveness, factual discipline, and persuasive clarity.
Do not judge which policy position you personally agree with.
Return only valid JSON.
""".strip(),
    "paraphrased": """
You are evaluating a two-sided debate as a neutral reviewer.
Choose the model whose advocacy of its assigned position is stronger.
Base the decision on reasoning quality, engagement with opposing points, care with factual claims, and clarity of persuasion.
Set aside your own view of the policies.
Output valid JSON only.
""".strip(),
}

OUTPUT_FIELDS = [
    "DebateId",
    "TopicId",
    "Model1name",
    "Model2name",
    "Model1Position",
    "starting",
    "PositionAStarts",
    "PromptVariant",
    "PromptSha256",
    "Judge",
    "Winner",
    "Confidence",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a paired diagnostic of judge-prompt phrasing sensitivity."
    )
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--topics", type=Path, default=DEFAULT_TOPICS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--judges", default=",".join(DEFAULT_JUDGES))
    parser.add_argument("--call-delay", type=int, default=10)
    parser.add_argument("--rate-limit-sleep", type=int, default=300)
    parser.add_argument("--max-new-calls", type=int)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_topic_lookup(path: Path) -> tuple[list[str], dict[tuple[str, str], str]]:
    topics = json.loads(path.read_text(encoding="utf-8"))
    order = [topic["id"] for topic in topics]
    lookup = {
        (topic["position_a"].strip(), topic["position_b"].strip()): topic["id"]
        for topic in topics
    }
    return order, lookup


def annotate_topics(
    rows: list[dict[str, str]], lookup: dict[tuple[str, str], str]
) -> list[dict[str, str]]:
    annotated = []
    for row in rows:
        key = (row["positionA"].strip(), row["positionB"].strip())
        if key not in lookup:
            raise ValueError(f"Could not map debate {row['DebateId']} to a topic.")
        item = dict(row)
        item["TopicId"] = lookup[key]
        annotated.append(item)
    return annotated


def select_balanced_sample(
    rows: list[dict[str, str]], topic_order: list[str]
) -> list[dict[str, str]]:
    pairs = sorted(
        {
            tuple(sorted((row["Model1name"], row["Model2name"])))
            for row in rows
        }
    )
    selected: list[dict[str, str]] = []

    for pair_index, pair in enumerate(pairs):
        topic_conditions = [
            (
                topic_order[pair_index % len(topic_order)],
                "A",
                "Model1" if pair_index % 2 == 0 else "Model2",
            ),
            (
                topic_order[(pair_index + 5) % len(topic_order)],
                "B",
                "Model2" if pair_index % 2 == 0 else "Model1",
            ),
        ]
        pair_rows = [
            row
            for row in rows
            if tuple(sorted((row["Model1name"], row["Model2name"]))) == pair
        ]
        for topic_id, model1_position, starting in topic_conditions:
            matches = [
                row
                for row in pair_rows
                if row["TopicId"] == topic_id
                and row["Model1Position"] == model1_position
                and row["starting"] == starting
            ]
            if len(matches) != 1:
                raise ValueError(
                    "Expected one row for "
                    f"{pair}, {topic_id}, Model1Position={model1_position}, "
                    f"starting={starting}; found {len(matches)}."
                )
            selected.append(matches[0])

    selected.sort(key=lambda row: int(row["DebateId"]))
    validate_sample(selected, len(pairs))
    return selected


def position_a_starts(row: dict[str, str]) -> str:
    starter_position = (
        row["Model1Position"]
        if row["starting"] == "Model1"
        else row["Model2Position"]
    )
    return "yes" if starter_position == "A" else "no"


def validate_sample(rows: list[dict[str, str]], pair_count: int) -> None:
    expected = pair_count * 2
    if len(rows) != expected:
        raise ValueError(f"Expected {expected} sampled debates, found {len(rows)}.")
    pair_counts = Counter(
        tuple(sorted((row["Model1name"], row["Model2name"]))) for row in rows
    )
    if set(pair_counts.values()) != {2}:
        raise ValueError(f"Model-pair sample is unbalanced: {pair_counts}")
    if Counter(row["Model1Position"] for row in rows) != {"A": 6, "B": 6}:
        raise ValueError("Model1 position assignment is not balanced.")
    if Counter(row["starting"] for row in rows) != {"Model1": 6, "Model2": 6}:
        raise ValueError("Model starting assignment is not balanced.")
    if Counter(position_a_starts(row) for row in rows) != {"yes": 6, "no": 6}:
        raise ValueError("Position starting assignment is not balanced.")


def read_output(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_output(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(
        rows,
        key=lambda row: (
            int(row["DebateId"]),
            row["Judge"],
            row["PromptVariant"],
        ),
    )
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(ordered)
    temporary.replace(path)


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def write_manifest(
    output_dir: Path,
    sample: list[dict[str, str]],
    judges: list[str],
) -> None:
    manifest = {
        "design": "paired fixed-transcript judge-prompt phrasing sensitivity",
        "sample_size_debates": len(sample),
        "prompt_variants": PROMPT_VARIANTS,
        "judges": judges,
        "temperature": 0.1,
        "max_tokens": 220,
        "sampling_rule": (
            "Two debates per unordered model pair; balanced Model1 position, "
            "starting model, and whether Position A starts; distributed over all topics."
        ),
        "debate_ids": [row["DebateId"] for row in sample],
        "sample": [
            {
                "debate_id": row["DebateId"],
                "topic_id": row["TopicId"],
                "model_1": row["Model1name"],
                "model_2": row["Model2name"],
                "model_1_position": row["Model1Position"],
                "starting": row["starting"],
                "position_a_starts": position_a_starts(row),
            }
            for row in sample
        ],
    }
    (output_dir / "experiment_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


def summarize(
    output_dir: Path,
    sample: list[dict[str, str]],
    judges: list[str],
    rows: list[dict[str, str]],
) -> None:
    by_key = {
        (row["DebateId"], row["Judge"], row["PromptVariant"]): row for row in rows
    }
    expected_pairs = len(sample) * len(judges)
    complete_pairs = []
    judge_stats = {}
    variant_counts = {
        variant: Counter(
            row["Winner"] for row in rows if row["PromptVariant"] == variant
        )
        for variant in PROMPT_VARIANTS
    }

    for judge in judges:
        stats = Counter()
        for debate in sample:
            a = by_key.get((debate["DebateId"], judge, "canonical"))
            b = by_key.get((debate["DebateId"], judge, "paraphrased"))
            if not a or not b:
                continue
            complete_pairs.append((a, b))
            if a["Winner"] == b["Winner"]:
                stats["exact_agreement"] += 1
                if a["Winner"] == "Tie":
                    stats["both_tie"] += 1
            elif "Tie" in {a["Winner"], b["Winner"]}:
                stats["tie_transition"] += 1
            else:
                stats["decisive_reversal"] += 1
            stats["complete"] += 1
        judge_stats[judge] = stats

    total = Counter()
    for stats in judge_stats.values():
        total.update(stats)

    lines = [
        "# Prompt-Phrasing Sensitivity Diagnostic",
        "",
        "## Design",
        "",
        (
            f"The study re-judges {len(sample)} fixed different-position debates "
            f"with two semantically equivalent prompt phrasings and {len(judges)} "
            f"cloud judges ({len(sample) * len(judges) * 2} planned calls)."
        ),
        (
            "The sample contains two debates per unordered model pair and is "
            "balanced for Model1 position, starting model, and whether Position A starts."
        ),
        (
            "Transcript, candidate labels, output schema, decoding temperature, "
            "and token limit are identical across prompt variants."
        ),
        "",
        "## Completion",
        "",
        f"- Completed calls: {len(rows)} / {len(sample) * len(judges) * 2}",
        f"- Complete paired comparisons: {len(complete_pairs)} / {expected_pairs}",
        "",
        "## Paired Verdict Stability",
        "",
        "| Judge | Pairs | Exact agreement | Decisive reversals | Tie transitions |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for judge in judges:
        stats = judge_stats[judge]
        complete = stats["complete"]
        agreement = (
            f"{stats['exact_agreement']} ({100 * stats['exact_agreement'] / complete:.1f}%)"
            if complete
            else "0"
        )
        lines.append(
            f"| {judge} | {complete} | {agreement} | "
            f"{stats['decisive_reversal']} | {stats['tie_transition']} |"
        )
    overall_agreement = (
        100 * total["exact_agreement"] / total["complete"]
        if total["complete"]
        else 0.0
    )
    lines.extend(
        [
            (
                f"| **All judges** | **{total['complete']}** | "
                f"**{total['exact_agreement']} ({overall_agreement:.1f}%)** | "
                f"**{total['decisive_reversal']}** | "
                f"**{total['tie_transition']}** |"
            ),
            "",
            "## Verdict Counts by Prompt",
            "",
            "| Prompt | Model1 wins | Model2 wins | Ties |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for variant in PROMPT_VARIANTS:
        counts = variant_counts[variant]
        model1_wins = sum(
            1
            for row in rows
            if row["PromptVariant"] == variant
            and row["Winner"]
            == next(
                debate["Model1name"]
                for debate in sample
                if debate["DebateId"] == row["DebateId"]
            )
        )
        model2_wins = sum(
            1
            for row in rows
            if row["PromptVariant"] == variant
            and row["Winner"]
            == next(
                debate["Model2name"]
                for debate in sample
                if debate["DebateId"] == row["DebateId"]
            )
        )
        lines.append(
            f"| {variant} | {model1_wins} | {model2_wins} | {counts['Tie']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            (
                "This is a small diagnostic on fixed transcripts. A verdict change "
                "shows that the observed judgment is not invariant to the tested "
                "wording, but one call per variant cannot fully distinguish prompt "
                "sensitivity from residual API nondeterminism. No human reference "
                "labels are available."
            ),
            "",
        ]
    )
    (output_dir / "PROMPT_PHRASING_ANALYSIS.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main() -> None:
    args = parse_args()
    judges = [judge.strip() for judge in args.judges.split(",") if judge.strip()]
    topic_order, topic_lookup = load_topic_lookup(args.topics)
    raw_rows = annotate_topics(read_raw_rows(args.raw), topic_lookup)
    present_topics = {row["TopicId"] for row in raw_rows}
    topic_order = [topic_id for topic_id in topic_order if topic_id in present_topics]
    if len(topic_order) != 10:
        raise ValueError(
            f"Expected 10 topics in the curated dataset, found {len(topic_order)}."
        )
    sample = select_balanced_sample(raw_rows, topic_order)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_manifest(args.output_dir, sample, judges)

    print(f"Selected debate IDs: {','.join(row['DebateId'] for row in sample)}")
    print(f"Planned calls: {len(sample) * len(judges) * len(PROMPT_VARIANTS)}")
    if args.dry_run:
        return

    output_path = args.output_dir / "prompt_phrasing_judgements.csv"
    output_rows = read_output(output_path)
    completed = {
        (row["DebateId"], row["Judge"], row["PromptVariant"])
        for row in output_rows
        if row.get("Winner") and row.get("Confidence")
    }
    new_calls = 0

    for sample_index, debate in enumerate(sample):
        variant_order = (
            ["canonical", "paraphrased"]
            if sample_index % 2 == 0
            else ["paraphrased", "canonical"]
        )
        _, user_prompt = diff_prompt(debate)
        for judge in judges:
            for variant in variant_order:
                key = (debate["DebateId"], judge, variant)
                if key in completed:
                    continue
                result = call_judge(
                    judge,
                    PROMPT_VARIANTS[variant],
                    user_prompt,
                    args.rate_limit_sleep,
                )
                winner = normalize_winner(
                    result.get("winner"),
                    [debate["Model1name"], debate["Model2name"], "Tie"],
                )
                row = {
                    "DebateId": debate["DebateId"],
                    "TopicId": debate["TopicId"],
                    "Model1name": debate["Model1name"],
                    "Model2name": debate["Model2name"],
                    "Model1Position": debate["Model1Position"],
                    "starting": debate["starting"],
                    "PositionAStarts": position_a_starts(debate),
                    "PromptVariant": variant,
                    "PromptSha256": prompt_hash(PROMPT_VARIANTS[variant]),
                    "Judge": judge,
                    "Winner": winner,
                    "Confidence": confidence_value(result.get("confidence")),
                }
                output_rows = [
                    existing
                    for existing in output_rows
                    if (
                        existing["DebateId"],
                        existing["Judge"],
                        existing["PromptVariant"],
                    )
                    != key
                ]
                output_rows.append(row)
                completed.add(key)
                write_output(output_path, output_rows)
                summarize(args.output_dir, sample, judges, output_rows)
                new_calls += 1
                print(
                    f"[{len(completed)}/{len(sample) * len(judges) * 2}] "
                    f"debate={debate['DebateId']} judge={judge} "
                    f"prompt={variant} winner={winner}",
                    flush=True,
                )
                if args.max_new_calls and new_calls >= args.max_new_calls:
                    print(f"Stopped after {new_calls} new calls.")
                    return
                time.sleep(args.call_delay)

    summarize(args.output_dir, sample, judges, output_rows)
    print(f"Complete: {len(output_rows)} judgments written to {output_path}")


if __name__ == "__main__":
    main()
