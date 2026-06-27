import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


RESULTS_DIR = Path("results")
METRICS = [
    "argument_quality",
    "evidence_specificity",
    "factfulness",
    "rebuttal_strength",
    "groundedness",
    "symmetry",
    "stance_consistency",
    "adaptability",
    "clarity",
    "overall_persuasiveness",
]


def load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Result file not found: {path}")

    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("Result JSON must contain a list of rows.")
        return [dict(row) for row in data]

    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8") as file:
            return list(csv.DictReader(file))

    raise ValueError("Input must be a .csv or .json benchmark result file.")


def find_latest_result(results_dir: Path) -> Path:
    candidates = [
        path
        for pattern in ("*_results.csv", "*_results.json")
        for path in results_dir.glob(pattern)
    ]
    if not candidates:
        raise FileNotFoundError("No benchmark result files found in results/. Run run_benchmark.py first or pass --input.")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def rounded(value: float | None, digits: int = 3) -> float | str:
    if value is None:
        return ""
    return round(value, digits)


def unsupported_count(value: Any) -> int:
    if value in (None, "", "[]"):
        return 0
    if isinstance(value, list):
        return len(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return 1
        if isinstance(parsed, list):
            return len(parsed)
        if parsed in (None, ""):
            return 0
        return 1
    return 1


def model_display(row: dict[str, Any], prefix: str) -> str:
    provider = str(row.get(f"{prefix}_provider") or "").strip()
    model = str(row.get(f"{prefix}_model") or "").strip()
    return f"{provider}:{model}" if provider and model else model


def judge_display(row: dict[str, Any]) -> str:
    provider = str(row.get("judge_provider") or "").strip()
    model = str(row.get("judge_model") or "").strip()
    return f"{provider}:{model}" if provider and model else model


def make_stat_bucket() -> dict[str, Any]:
    return {
        "debates": 0,
        "wins": 0,
        "ties": 0,
        "win_confidences": [],
        "unsupported_claims": 0,
        "metrics": defaultdict(list),
    }


def add_metric_values(bucket: dict[str, Any], row: dict[str, Any], prefix: str) -> None:
    for metric in METRICS:
        value = to_float(row.get(f"{prefix}_{metric}"))
        if value is not None:
            bucket["metrics"][metric].append(value)


def summarize_bucket(name: str, bucket: dict[str, Any]) -> dict[str, Any]:
    debates = bucket["debates"]
    wins = bucket["wins"]
    ties = bucket["ties"]
    summary: dict[str, Any] = {
        "name": name,
        "debates": debates,
        "wins": wins,
        "losses": max(debates - wins - ties, 0),
        "ties": ties,
        "win_rate": rounded(wins / debates if debates else None),
        "tie_rate": rounded(ties / debates if debates else None),
        "avg_win_confidence": rounded(average(bucket["win_confidences"])),
        "unsupported_claims": bucket["unsupported_claims"],
    }
    for metric in METRICS:
        summary[f"avg_{metric}"] = rounded(average(bucket["metrics"][metric]))
    return summary


def analyze(rows: list[dict[str, Any]], input_path: Path) -> dict[str, Any]:
    model_stats: dict[str, dict[str, Any]] = defaultdict(make_stat_bucket)
    role_model_stats: dict[tuple[str, str], dict[str, Any]] = defaultdict(make_stat_bucket)
    benchmark_model_stats: dict[tuple[str, str], dict[str, Any]] = defaultdict(make_stat_bucket)
    position_stats: dict[str, dict[str, Any]] = defaultdict(make_stat_bucket)
    start_style_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"debates": 0, "confidence": [], "agent_a_wins": 0, "agent_b_wins": 0, "ties": 0})
    topic_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"debates": 0, "confidence": [], "agent_a_wins": 0, "agent_b_wins": 0, "ties": 0})
    role_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"debates": 0, "confidence": [], "agent_a_wins": 0, "agent_b_wins": 0, "ties": 0})
    benchmark_mode_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"debates": 0, "confidence": [], "agent_a_wins": 0, "agent_b_wins": 0, "ties": 0})
    judge_mode_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"debates": 0, "confidence": [], "agent_a_wins": 0, "agent_b_wins": 0, "ties": 0})
    judge_model_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"debates": 0, "confidence": [], "agent_a_wins": 0, "agent_b_wins": 0, "ties": 0})
    judge_agreement_groups: dict[str, dict[str, str]] = defaultdict(dict)
    position_a_overall: list[float] = []
    position_b_overall: list[float] = []
    score_diffs: list[float] = []
    debate_ids = {str(row.get("debate_id") or index) for index, row in enumerate(rows)}

    for row in rows:
        winner = row.get("winner", "")
        confidence = to_float(row.get("confidence"))
        position_a_model = model_display(row, "position_a")
        position_b_model = model_display(row, "position_b")
        benchmark_mode = str(row.get("benchmark_mode") or "legacy")
        judge_mode = str(row.get("judge_mode") or "legacy")
        judge_model = judge_display(row) or "unknown"
        debate_id = str(row.get("debate_id") or "")
        if debate_id and judge_mode:
            judge_agreement_groups[f"{debate_id}|{judge_model}"][judge_mode] = winner

        participants = [
            ("Position A", "position_a", position_a_model, winner == "Agent A"),
            ("Position B", "position_b", position_b_model, winner == "Agent B"),
        ]

        for position_name, prefix, model, won in participants:
            if model:
                model_bucket = model_stats[model]
                model_bucket["debates"] += 1
                add_metric_values(model_bucket, row, prefix)
                model_bucket["unsupported_claims"] += unsupported_count(row.get(f"{prefix}_unsupported_claims"))
                if won:
                    model_bucket["wins"] += 1
                    if confidence is not None:
                        model_bucket["win_confidences"].append(confidence)
                elif winner == "Tie":
                    model_bucket["ties"] += 1

                for grouped_bucket in (
                    role_model_stats[(position_name, model)],
                    benchmark_model_stats[(benchmark_mode, model)],
                ):
                    grouped_bucket["debates"] += 1
                    add_metric_values(grouped_bucket, row, prefix)
                    grouped_bucket["unsupported_claims"] += unsupported_count(row.get(f"{prefix}_unsupported_claims"))
                    if won:
                        grouped_bucket["wins"] += 1
                        if confidence is not None:
                            grouped_bucket["win_confidences"].append(confidence)
                    elif winner == "Tie":
                        grouped_bucket["ties"] += 1

            position_bucket = position_stats[position_name]
            position_bucket["debates"] += 1
            add_metric_values(position_bucket, row, prefix)
            position_bucket["unsupported_claims"] += unsupported_count(row.get(f"{prefix}_unsupported_claims"))
            if won:
                position_bucket["wins"] += 1
                if confidence is not None:
                    position_bucket["win_confidences"].append(confidence)
            elif winner == "Tie":
                position_bucket["ties"] += 1

        for group_key, stats in (
            (str(row.get("start_style") or "unknown"), start_style_stats),
            (str(row.get("topic_id") or "unknown"), topic_stats),
            (str(row.get("role_assignment") or "unknown"), role_stats),
            (benchmark_mode, benchmark_mode_stats),
            (judge_mode, judge_mode_stats),
            (judge_model, judge_model_stats),
        ):
            group = stats[group_key]
            group["debates"] += 1
            if confidence is not None:
                group["confidence"].append(confidence)
            if winner == "Agent A":
                group["agent_a_wins"] += 1
            elif winner == "Agent B":
                group["agent_b_wins"] += 1
            elif winner == "Tie":
                group["ties"] += 1

        a_overall = to_float(row.get("position_a_overall_persuasiveness"))
        b_overall = to_float(row.get("position_b_overall_persuasiveness"))
        if a_overall is not None:
            position_a_overall.append(a_overall)
        if b_overall is not None:
            position_b_overall.append(b_overall)
        if a_overall is not None and b_overall is not None:
            score_diffs.append(a_overall - b_overall)

    return {
        "input": str(input_path),
        "rows": len(rows),
        "unique_debates": len(debate_ids),
        "debates": len(rows),
        "overall": {
            "avg_confidence": rounded(average([value for row in rows if (value := to_float(row.get("confidence"))) is not None])),
            "position_a_win_rate": rounded(position_stats["Position A"]["wins"] / len(rows) if rows else None),
            "position_b_win_rate": rounded(position_stats["Position B"]["wins"] / len(rows) if rows else None),
            "tie_rate": rounded(sum(1 for row in rows if row.get("winner") == "Tie") / len(rows) if rows else None),
            "avg_position_a_overall_persuasiveness": rounded(average(position_a_overall)),
            "avg_position_b_overall_persuasiveness": rounded(average(position_b_overall)),
            "avg_position_a_minus_b_overall_persuasiveness": rounded(average(score_diffs)),
        },
        "model_summary": sorted(
            [summarize_bucket(model, bucket) for model, bucket in model_stats.items()],
            key=lambda item: (-float(item["win_rate"] or 0), item["name"]),
        ),
        "role_model_summary": summarize_grouped_model_buckets(role_model_stats, "role"),
        "benchmark_model_summary": summarize_grouped_model_buckets(benchmark_model_stats, "benchmark_mode"),
        "position_summary": [summarize_bucket(name, position_stats[name]) for name in ("Position A", "Position B")],
        "start_style_summary": summarize_group_counts(start_style_stats, "start_style"),
        "topic_summary": summarize_group_counts(topic_stats, "topic_id"),
        "role_assignment_summary": summarize_group_counts(role_stats, "role_assignment"),
        "benchmark_mode_summary": summarize_group_counts(benchmark_mode_stats, "benchmark_mode"),
        "judge_mode_summary": summarize_group_counts(judge_mode_stats, "judge_mode"),
        "judge_model_summary": summarize_group_counts(judge_model_stats, "judge_model"),
        "judge_mode_agreement": summarize_judge_mode_agreement(judge_agreement_groups),
    }


def summarize_grouped_model_buckets(stats: dict[tuple[str, str], dict[str, Any]], group_key: str) -> list[dict[str, Any]]:
    rows = []
    for (group_name, model), bucket in stats.items():
        row = summarize_bucket(model, bucket)
        row[group_key] = group_name
        rows.append(row)
    return sorted(rows, key=lambda item: (str(item[group_key]), -float(item["win_rate"] or 0), item["name"]))


def summarize_judge_mode_agreement(groups: dict[str, dict[str, str]]) -> dict[str, Any]:
    comparable = [winners for winners in groups.values() if len(winners) > 1]
    if not comparable:
        return {"comparable_debates": 0, "agreement_count": 0, "agreement_rate": ""}

    agreement_count = sum(1 for winners in comparable if len(set(winners.values())) == 1)
    disagreements = [
        {"debate_id": debate_id, "winners_by_judge_mode": winners}
        for debate_id, winners in groups.items()
        if len(winners) > 1 and len(set(winners.values())) > 1
    ]
    return {
        "comparable_debates": len(comparable),
        "agreement_count": agreement_count,
        "agreement_rate": rounded(agreement_count / len(comparable)),
        "disagreements": disagreements,
    }


def summarize_group_counts(stats: dict[str, dict[str, Any]], name_key: str) -> list[dict[str, Any]]:
    rows = []
    for name, bucket in stats.items():
        debates = bucket["debates"]
        rows.append(
            {
                name_key: name,
                "debates": debates,
                "agent_a_wins": bucket["agent_a_wins"],
                "agent_b_wins": bucket["agent_b_wins"],
                "ties": bucket["ties"],
                "position_a_win_rate": rounded(bucket["agent_a_wins"] / debates if debates else None),
                "position_b_win_rate": rounded(bucket["agent_b_wins"] / debates if debates else None),
                "avg_confidence": rounded(average(bucket["confidence"])),
            }
        )
    return sorted(rows, key=lambda item: str(item[name_key]))


def table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "No rows."

    widths = {
        column: max(len(column), *(len(str(row.get(column, ""))) for row in rows))
        for column in columns
    }
    header = "| " + " | ".join(column.ljust(widths[column]) for column in columns) + " |"
    separator = "| " + " | ".join("-" * widths[column] for column in columns) + " |"
    body = [
        "| " + " | ".join(str(row.get(column, "")).ljust(widths[column]) for column in columns) + " |"
        for row in rows
    ]
    return "\n".join([header, separator, *body])


def render_markdown(analysis: dict[str, Any]) -> str:
    lines = [
        "# Benchmark Aggregate Analysis",
        "",
        f"Input: `{analysis['input']}`",
        f"Result rows / judge evaluations: `{analysis['rows']}`",
        f"Unique debates: `{analysis['unique_debates']}`",
        "",
        "## Overall",
        "",
        table([analysis["overall"]], list(analysis["overall"].keys())),
        "",
        "## Model Summary",
        "",
        table(
            analysis["model_summary"],
            [
                "name",
                "debates",
                "wins",
                "losses",
                "ties",
                "win_rate",
                "avg_win_confidence",
                "avg_overall_persuasiveness",
                "avg_factfulness",
                "avg_groundedness",
                "unsupported_claims",
            ],
        ),
        "",
        "## Role Leaderboard",
        "",
        table(
            analysis["role_model_summary"],
            [
                "role",
                "name",
                "debates",
                "wins",
                "losses",
                "ties",
                "win_rate",
                "avg_overall_persuasiveness",
                "avg_factfulness",
                "avg_groundedness",
                "unsupported_claims",
            ],
        ),
        "",
        "## Benchmark Mode Leaderboard",
        "",
        table(
            analysis["benchmark_model_summary"],
            [
                "benchmark_mode",
                "name",
                "debates",
                "wins",
                "losses",
                "ties",
                "win_rate",
                "avg_overall_persuasiveness",
                "avg_factfulness",
                "avg_groundedness",
            ],
        ),
        "",
        "## Position Summary",
        "",
        table(
            analysis["position_summary"],
            [
                "name",
                "debates",
                "wins",
                "losses",
                "ties",
                "win_rate",
                "avg_overall_persuasiveness",
                "avg_factfulness",
                "avg_groundedness",
                "unsupported_claims",
            ],
        ),
        "",
        "## Start Style Summary",
        "",
        table(analysis["start_style_summary"], ["start_style", "debates", "agent_a_wins", "agent_b_wins", "ties", "position_a_win_rate", "position_b_win_rate", "avg_confidence"]),
        "",
        "## Benchmark Mode Summary",
        "",
        table(analysis["benchmark_mode_summary"], ["benchmark_mode", "debates", "agent_a_wins", "agent_b_wins", "ties", "position_a_win_rate", "position_b_win_rate", "avg_confidence"]),
        "",
        "## Judge Mode Summary",
        "",
        table(analysis["judge_mode_summary"], ["judge_mode", "debates", "agent_a_wins", "agent_b_wins", "ties", "position_a_win_rate", "position_b_win_rate", "avg_confidence"]),
        "",
        "## Judge Model Summary",
        "",
        table(analysis["judge_model_summary"], ["judge_model", "debates", "agent_a_wins", "agent_b_wins", "ties", "position_a_win_rate", "position_b_win_rate", "avg_confidence"]),
        "",
        "## Judge Mode Agreement",
        "",
        table([analysis["judge_mode_agreement"]], ["comparable_debates", "agreement_count", "agreement_rate"]),
        "",
        "## Role Assignment Summary",
        "",
        table(analysis["role_assignment_summary"], ["role_assignment", "debates", "agent_a_wins", "agent_b_wins", "ties", "position_a_win_rate", "position_b_win_rate", "avg_confidence"]),
        "",
        "## Topic Summary",
        "",
        table(analysis["topic_summary"], ["topic_id", "debates", "agent_a_wins", "agent_b_wins", "ties", "position_a_win_rate", "position_b_win_rate", "avg_confidence"]),
    ]
    return "\n".join(lines)


def write_analysis_files(analysis: dict[str, Any], output_dir: Path, output_prefix: str | None) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = output_prefix or datetime.now().strftime("%Y%m%d_%H%M%S_analysis")
    json_path = output_dir / f"{prefix}.json"
    markdown_path = output_dir / f"{prefix}.md"
    json_path.write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")
    markdown_path.write_text(render_markdown(analysis), encoding="utf-8")
    return json_path, markdown_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze aggregate results from run_benchmark.py outputs.")
    parser.add_argument("--input", help="Path to a benchmark *_results.csv or *_results.json file. Defaults to the latest result in results/.")
    parser.add_argument("--output-dir", default=str(RESULTS_DIR), help="Directory for written analysis files.")
    parser.add_argument("--output-prefix", help="Filename prefix for --write-files outputs.")
    parser.add_argument("--write-files", action="store_true", help="Write analysis JSON and Markdown files.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input) if args.input else find_latest_result(RESULTS_DIR)
    rows = load_rows(input_path)
    analysis = analyze(rows, input_path)
    print(render_markdown(analysis))

    if args.write_files:
        json_path, markdown_path = write_analysis_files(analysis, Path(args.output_dir), args.output_prefix)
        print("\nAnalysis files written")
        print(f"JSON: {json_path}")
        print(f"Markdown: {markdown_path}")


if __name__ == "__main__":
    main()
