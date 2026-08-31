import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path


DEFAULT_INPUT_DIR = Path("runs/2026-08-28_repeated_judgment_stability")
DEFAULT_OUTPUT_DIR = DEFAULT_INPUT_DIR / "analysis"
EXPECTED_DEBATES = 240
EXPECTED_JUDGES = 3
EXPECTED_REPEATS = 5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze repeated cloud-judgment stability.")
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


def normalized_label(row: dict[str, str]) -> str:
    if row["Winner"] == row["Model1name"]:
        return "Model1"
    if row["Winner"] == row["Model2name"]:
        return "Model2"
    if row["Winner"] == "Tie":
        return "Tie"
    raise ValueError(f"Invalid winner in debate {row['DebateId']}: {row['Winner']}")


def normalized_entropy(labels: list[str]) -> float:
    counts = Counter(labels)
    entropy = -sum((count / len(labels)) * math.log(count / len(labels)) for count in counts.values())
    return entropy / math.log(3)


def average_ranks(scores: dict[str, float]) -> dict[str, float]:
    ordered = sorted(scores, key=lambda model: (-scores[model], model))
    ranks: dict[str, float] = {}
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and scores[ordered[end]] == scores[ordered[index]]:
            end += 1
        rank = statistics.mean(range(index + 1, end + 1))
        for model in ordered[index:end]:
            ranks[model] = rank
        index = end
    return ranks


def model_repeat_rankings(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    by_judge_repeat: dict[tuple[str, int], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_judge_repeat[(row["Judge"], int(row["RepeatIndex"]))].append(row)

    output: list[dict[str, object]] = []
    for (judge, repeat), subset in sorted(by_judge_repeat.items()):
        points: Counter[str] = Counter()
        evaluations: Counter[str] = Counter()
        for row in subset:
            model1 = row["Model1name"]
            model2 = row["Model2name"]
            evaluations.update([model1, model2])
            if row["Winner"] == model1:
                points[model1] += 1.0
            elif row["Winner"] == model2:
                points[model2] += 1.0
            else:
                points[model1] += 0.5
                points[model2] += 0.5
        scores = {model: points[model] / evaluations[model] for model in sorted(evaluations)}
        ranks = average_ranks(scores)
        for model in sorted(scores):
            output.append(
                {
                    "Judge": judge,
                    "RepeatIndex": repeat,
                    "Model": model,
                    "Evaluations": evaluations[model],
                    "TieAdjustedWinRate": round(scores[model], 4),
                    "Rank": ranks[model],
                }
            )
    return output


def summarize_rank_variation(rank_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rank_rows:
        grouped[(str(row["Judge"]), str(row["Model"]))].append(float(row["Rank"]))
    output = []
    for (judge, model), ranks in sorted(grouped.items()):
        output.append(
            {
                "Judge": judge,
                "Model": model,
                "Repeats": len(ranks),
                "MeanRank": round(statistics.mean(ranks), 3),
                "RankStdDev": round(statistics.stdev(ranks), 3) if len(ranks) > 1 else 0.0,
                "BestRank": min(ranks),
                "WorstRank": max(ranks),
            }
        )
    return output


def markdown_table(rows: list[dict[str, object]], fields: list[tuple[str, str]]) -> str:
    header = "| " + " | ".join(label for _, label in fields) + " |"
    divider = "| " + " | ".join("---:" if index else "---" for index, _ in enumerate(fields)) + " |"
    body = ["| " + " | ".join(str(row[field]) for field, _ in fields) + " |" for row in rows]
    return "\n".join([header, divider, *body])


def main() -> None:
    args = parse_args()
    files = sorted(args.input_dir.glob("judgements_*.csv"))
    if not files:
        raise FileNotFoundError(f"No judgement CSVs found in {args.input_dir}")
    rows = [row for path in files for row in read_csv(path)]
    rows.sort(key=lambda row: (row["Judge"], int(row["DebateId"]), int(row["RepeatIndex"])))

    keys = [(row["DebateId"], row["Judge"], row["RepeatIndex"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate DebateId/Judge/RepeatIndex keys")
    judges = sorted({row["Judge"] for row in rows})
    expected_rows = EXPECTED_DEBATES * EXPECTED_JUDGES * EXPECTED_REPEATS
    if not args.allow_incomplete and (len(rows) != expected_rows or len(judges) != EXPECTED_JUDGES):
        raise ValueError(
            f"Incomplete experiment: rows={len(rows)}/{expected_rows}, judges={len(judges)}/{EXPECTED_JUDGES}"
        )

    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(row["DebateId"], row["Judge"])].append(row)

    complete_groups = {
        key: sorted(group, key=lambda row: int(row["RepeatIndex"]))
        for key, group in groups.items()
        if {int(row["RepeatIndex"]) for row in group} == set(range(1, EXPECTED_REPEATS + 1))
    }
    detail_rows: list[dict[str, object]] = []
    for (debate_id, judge), group in sorted(
        complete_groups.items(), key=lambda item: (item[0][1], int(item[0][0]))
    ):
        labels = [normalized_label(row) for row in group]
        counts = Counter(labels)
        modal_count = max(counts.values())
        pair_matches = sum(left == right for left, right in combinations(labels, 2))
        detail_rows.append(
            {
                "DebateId": debate_id,
                "TopicId": group[0]["TopicId"],
                "Judge": judge,
                "WinnerSequence": ";".join(labels),
                "UniqueWinners": len(counts),
                "Unanimous": "yes" if len(counts) == 1 else "no",
                "ModalShare": round(modal_count / EXPECTED_REPEATS, 3),
                "PairwiseAgreement": round(pair_matches / math.comb(EXPECTED_REPEATS, 2), 3),
                "NormalizedEntropy": round(normalized_entropy(labels), 3),
                "OriginalRepeatAgreement": round(
                    sum(labels[0] == label for label in labels[1:]) / (EXPECTED_REPEATS - 1), 3
                ),
            }
        )

    judge_summary = []
    for judge in judges:
        subset = [row for row in detail_rows if row["Judge"] == judge]
        evaluation_rows = [row for row in rows if row["Judge"] == judge]
        judge_summary.append(
            {
                "Judge": judge,
                "Rows": len(evaluation_rows),
                "CompleteGroups": len(subset),
                "UnanimousGroups": sum(row["Unanimous"] == "yes" for row in subset),
                "UnanimousRate": round(
                    sum(row["Unanimous"] == "yes" for row in subset) / len(subset), 3
                )
                if subset
                else 0.0,
                "MeanPairwiseAgreement": round(
                    statistics.mean(float(row["PairwiseAgreement"]) for row in subset), 3
                )
                if subset
                else 0.0,
                "MeanModalShare": round(statistics.mean(float(row["ModalShare"]) for row in subset), 3)
                if subset
                else 0.0,
                "MeanNormalizedEntropy": round(
                    statistics.mean(float(row["NormalizedEntropy"]) for row in subset), 3
                )
                if subset
                else 0.0,
                "OriginalRepeatAgreement": round(
                    statistics.mean(float(row["OriginalRepeatAgreement"]) for row in subset), 3
                )
                if subset
                else 0.0,
                "TieRate": round(
                    sum(row["Winner"] == "Tie" for row in evaluation_rows) / len(evaluation_rows), 3
                )
                if evaluation_rows
                else 0.0,
            }
        )

    rank_rows = model_repeat_rankings(rows)
    rank_variation = summarize_rank_variation(rank_rows)
    summary = {
        "design": {
            "debates": EXPECTED_DEBATES,
            "judges": judges,
            "repeats_per_debate_judge": EXPECTED_REPEATS,
            "expected_rows": expected_rows,
            "observed_rows": len(rows),
            "complete_debate_judge_groups": len(complete_groups),
            "expected_debate_judge_groups": EXPECTED_DEBATES * EXPECTED_JUDGES,
            "temperature": 0.1,
            "max_tokens": 220,
        },
        "judge_summary": judge_summary,
        "rank_variation": rank_variation,
    }

    report = f"""# Repeated-Judgment Stability

## Design

The experiment evaluates all {EXPECTED_DEBATES} fixed different-position transcripts five times with each of three cloud judges. The transcript, candidate labels, prompt, temperature (0.1), and output limit (220 tokens) are fixed. The original curated verdict is repetition 1 and four additional API calls provide repetitions 2--5. The complete design contains {expected_rows:,} judgments in {EXPECTED_DEBATES * EXPECTED_JUDGES} transcript--judge groups.

Current progress: {len(rows):,}/{expected_rows:,} rows and {len(complete_groups)}/{EXPECTED_DEBATES * EXPECTED_JUDGES} complete five-repeat groups.

## Judge-Level Stability

{markdown_table(judge_summary, [('Judge', 'Judge'), ('Rows', 'Rows'), ('CompleteGroups', 'Complete groups'), ('UnanimousRate', 'Unanimous rate'), ('MeanPairwiseAgreement', 'Pairwise agreement'), ('MeanModalShare', 'Modal share'), ('MeanNormalizedEntropy', 'Normalized entropy'), ('OriginalRepeatAgreement', 'Original-repeat agreement'), ('TieRate', 'Tie rate')])}

Unanimous rate is the fraction of fixed transcripts receiving the same winner in all five evaluations. Pairwise agreement averages the ten repeat-pair comparisons within each complete group. Normalized entropy is zero for a fully stable group and one when verdict mass is evenly distributed across Model 1, Model 2, and tie. Original-repeat agreement compares the curated verdict with each of the four new calls.

## Interpretation Boundary

Only complete five-repeat groups enter the stability statistics. These measurements estimate cloud-judge repeatability under the recorded API conditions; they do not establish agreement with human persuasion judgments.
"""

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "RepeatedJudgements.csv", rows)
    write_csv(args.output_dir / "group_stability.csv", detail_rows)
    write_csv(args.output_dir / "judge_summary.csv", judge_summary)
    write_csv(args.output_dir / "model_repeat_rankings.csv", rank_rows)
    write_csv(args.output_dir / "model_rank_variation.csv", rank_variation)
    (args.output_dir / "analysis_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (args.output_dir / "ANALYSIS_REPORT.md").write_text(report, encoding="utf-8")
    print(
        f"Wrote stability analysis: rows={len(rows)}/{expected_rows}, "
        f"complete_groups={len(complete_groups)}/{EXPECTED_DEBATES * EXPECTED_JUDGES}"
    )


if __name__ == "__main__":
    main()
