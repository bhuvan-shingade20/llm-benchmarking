import argparse
import csv
import json
import statistics
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path


DEFAULT_TOPICS = Path("topics/ideology_topics.json")
DEFAULT_INPUT_DIR = Path("runs/2026-08-28_ideological_persuasion/annotations")
DEFAULT_OUTPUT_DIR = Path("runs/2026-08-28_ideological_persuasion/annotation_analysis")
EXPECTED_ANNOTATORS = 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate ideological topic annotations.")
    parser.add_argument("--topics", type=Path, default=DEFAULT_TOPICS)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--allow-incomplete", action="store_true")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def sign_label(score: float) -> str:
    if score < 0:
        return "liberal"
    if score > 0:
        return "conservative"
    return "mixed_or_neutral"


def majority(values: list[str]) -> tuple[str, int]:
    value, count = Counter(values).most_common(1)[0]
    return value, count


def main() -> None:
    args = parse_args()
    topics = json.loads(args.topics.read_text(encoding="utf-8"))
    if args.config:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        selected_ids = config["generated_debates"]["topic_ids"]
        topic_by_id = {topic["id"]: topic for topic in topics}
        missing = sorted(set(selected_ids) - set(topic_by_id))
        if missing:
            raise ValueError(f"Unknown configured topic ids: {missing}")
        topics = [topic_by_id[topic_id] for topic_id in selected_ids]
    topic_by_id = {topic["id"]: topic for topic in topics}
    files = sorted(args.input_dir.glob("annotations_*.csv"))
    rows = [row for path in files for row in read_csv(path)]
    keys = [(row["TopicId"], row["Annotator"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate TopicId/Annotator keys")
    annotators = sorted({row["Annotator"] for row in rows})
    expected_rows = len(topics) * EXPECTED_ANNOTATORS
    if not args.allow_incomplete and (
        len(rows) != expected_rows or len(annotators) != EXPECTED_ANNOTATORS
    ):
        raise ValueError(
            f"Incomplete annotations: rows={len(rows)}/{expected_rows}, "
            f"annotators={len(annotators)}/{EXPECTED_ANNOTATORS}"
        )

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row["TopicId"] not in topic_by_id:
            raise ValueError(f"Unknown topic in annotations: {row['TopicId']}")
        grouped[row["TopicId"]].append(row)

    topic_summary: list[dict[str, object]] = []
    validated_topics = []
    pairwise_sign_matches = 0
    pairwise_sign_total = 0
    score_differences = []
    for topic in topics:
        subset = grouped.get(topic["id"], [])
        labels_a = [row["PositionALabel"] for row in subset]
        labels_b = [row["PositionBLabel"] for row in subset]
        scores_a = [int(row["PositionAScore"]) for row in subset]
        scores_b = [int(row["PositionBScore"]) for row in subset]
        relevant_count = sum(row["PoliticallyRelevant"] == "yes" for row in subset)
        majority_a, count_a = majority(labels_a) if labels_a else ("missing", 0)
        majority_b, count_b = majority(labels_b) if labels_b else ("missing", 0)
        complete = len(subset) == EXPECTED_ANNOTATORS
        intended_match = (
            majority_a == topic["intended_position_a_label"]
            and majority_b == topic["intended_position_b_label"]
        )
        accepted = (
            complete
            and relevant_count >= 2
            and count_a >= 2
            and count_b >= 2
            and majority_a != "mixed_or_neutral"
            and majority_b != "mixed_or_neutral"
            and majority_a != majority_b
            and intended_match
        )
        median_a = statistics.median(scores_a) if scores_a else 0
        median_b = statistics.median(scores_b) if scores_b else 0
        topic_summary.append(
            {
                "TopicId": topic["id"],
                "Domain": topic["domain"],
                "Annotations": len(subset),
                "RelevantVotes": relevant_count,
                "PositionAMajority": majority_a,
                "PositionAAgreement": count_a,
                "PositionAMedianScore": median_a,
                "PositionBMajority": majority_b,
                "PositionBAgreement": count_b,
                "PositionBMedianScore": median_b,
                "IntendedLabelsMatch": "yes" if intended_match else "no",
                "Accepted": "yes" if accepted else "no",
            }
        )
        if accepted:
            item = dict(topic)
            item["validated_position_a_label"] = majority_a
            item["validated_position_b_label"] = majority_b
            item["position_a_median_score"] = median_a
            item["position_b_median_score"] = median_b
            validated_topics.append(item)

        for field in ("PositionALabel", "PositionBLabel"):
            values = [row[field] for row in subset]
            for left, right in combinations(values, 2):
                pairwise_sign_matches += left == right
                pairwise_sign_total += 1
        for field in ("PositionAScore", "PositionBScore"):
            values = [int(row[field]) for row in subset]
            score_differences.extend(abs(left - right) for left, right in combinations(values, 2))

    complete_topics = sum(row["Annotations"] == EXPECTED_ANNOTATORS for row in topic_summary)
    accepted_count = sum(row["Accepted"] == "yes" for row in topic_summary)
    summary = {
        "topics": len(topics),
        "annotators": annotators,
        "expected_rows": expected_rows,
        "observed_rows": len(rows),
        "complete_topics": complete_topics,
        "accepted_topics": accepted_count,
        "pairwise_direction_agreement": round(pairwise_sign_matches / pairwise_sign_total, 3)
        if pairwise_sign_total
        else 0.0,
        "mean_absolute_score_difference": round(statistics.mean(score_differences), 3)
        if score_differences
        else 0.0,
        "acceptance_rule": (
            "three annotations; at least two politically relevant votes; majority non-neutral, "
            "opposing direction labels for both positions; majority labels match the pre-specified mapping"
        ),
    }

    report = f"""# Ideological Topic Annotation Validation

## Protocol

Three independent cloud models annotate each proposition on a five-point scale from strongly liberal (-2) to strongly conservative (+2) in contemporary U.S. political discourse. Annotators do not see the pre-specified labels. A topic is accepted only when all three annotations are present, at least two annotators mark it politically relevant, both positions receive non-neutral opposing majority labels, and those labels match the mapping fixed before annotation.

## Current Status

- Annotation rows: {len(rows)}/{expected_rows}
- Complete topics: {complete_topics}/{len(topics)}
- Accepted topics: {accepted_count}/{len(topics)}
- Pairwise ideological-direction agreement: {summary['pairwise_direction_agreement']}
- Mean absolute difference on the five-point score: {summary['mean_absolute_score_difference']}

No debate generation should begin until the complete panel passes this validation or rejected topics are replaced and re-annotated.
"""

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "topic_annotation_summary.csv", topic_summary)
    (args.output_dir / "analysis_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (args.output_dir / "validated_ideology_topics.json").write_text(
        json.dumps(validated_topics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (args.output_dir / "ANNOTATION_REPORT.md").write_text(report, encoding="utf-8")
    print(
        f"Wrote annotation analysis: rows={len(rows)}/{expected_rows}, "
        f"accepted={accepted_count}/{len(topics)}"
    )


if __name__ == "__main__":
    main()
