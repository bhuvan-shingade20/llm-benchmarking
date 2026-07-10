import csv
import glob
from collections import defaultdict
from pathlib import Path
from typing import Any


RESULTS_PATTERN = "results/*_results.csv"
OUTPUT_PATH = Path("results/model_ranking_all_runs.md")
ALT_OUTPUT_PATH = Path("results/all_model_rankings.md")
VALID_WINNERS = {"Agent A", "Agent B", "Tie"}


def safe_float(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def provider_label(provider: str, model: str) -> str:
    provider = (provider or "").strip().lower()
    if provider == "ollama" or model.startswith("ollama:"):
        return "ollama"
    return "academic_cloud"


def model_name(provider: str, model: str) -> str:
    model = (model or "").strip()
    if model.startswith("ollama:") or model.startswith("openai:"):
        return model.split(":", 1)[1]
    return model


def average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def fmt(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{value:.{digits}f}"


def metric(row: dict[str, str], prefix: str, name: str) -> float | None:
    return safe_float(row.get(f"{prefix}_{name}"))


def read_rows() -> tuple[list[str], list[dict[str, str]]]:
    files = sorted(glob.glob(RESULTS_PATTERN))
    rows: list[dict[str, str]] = []
    for path in files:
        with open(path, newline="", encoding="utf-8") as file:
            rows.extend(csv.DictReader(file))
    return files, rows


def collect_stats(rows: list[dict[str, str]]) -> tuple[dict[tuple[str, str], dict[str, Any]], list[dict[str, str]]]:
    stats: dict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "debates": 0,
            "wins": 0,
            "losses": 0,
            "ties": 0,
            "overall_persuasiveness": [],
            "factfulness": [],
            "groundedness": [],
            "confidence": [],
        }
    )
    valid_rows: list[dict[str, str]] = []

    for row in rows:
        winner = row.get("winner", "")
        if winner not in VALID_WINNERS:
            continue

        position_a_model = model_name(row.get("position_a_provider", ""), row.get("position_a_model", ""))
        position_b_model = model_name(row.get("position_b_provider", ""), row.get("position_b_model", ""))
        if not position_a_model or not position_b_model:
            continue

        valid_rows.append(row)
        confidence = safe_float(row.get("confidence"))
        participants = [
            (
                provider_label(row.get("position_a_provider", ""), row.get("position_a_model", "")),
                position_a_model,
                "position_a",
                winner == "Agent A",
            ),
            (
                provider_label(row.get("position_b_provider", ""), row.get("position_b_model", "")),
                position_b_model,
                "position_b",
                winner == "Agent B",
            ),
        ]

        for provider, model, prefix, won in participants:
            item = stats[(provider, model)]
            item["debates"] += 1
            if confidence is not None:
                item["confidence"].append(confidence)
            if won:
                item["wins"] += 1
            elif winner == "Tie":
                item["ties"] += 1
            else:
                item["losses"] += 1

            for metric_name in ("overall_persuasiveness", "factfulness", "groundedness"):
                value = metric(row, prefix, metric_name)
                if value is not None:
                    item[metric_name].append(value)

    return stats, valid_rows


def build_report(files: list[str], rows: list[dict[str, str]], valid_rows: list[dict[str, str]], stats: dict[tuple[str, str], dict[str, Any]]) -> str:
    ranking = []
    for (provider, model), item in stats.items():
        debates = item["debates"]
        if debates == 0:
            continue
        ranking.append(
            {
                "provider": provider,
                "model": model,
                "debates": debates,
                "wins": item["wins"],
                "losses": item["losses"],
                "ties": item["ties"],
                "win_rate": item["wins"] / debates,
                "avg_overall": average(item["overall_persuasiveness"]),
                "avg_factfulness": average(item["factfulness"]),
                "avg_groundedness": average(item["groundedness"]),
                "avg_confidence": average(item["confidence"]),
            }
        )
    ranking.sort(key=lambda item: (-item["win_rate"], -item["wins"], item["model"]))

    valid_run_ids = sorted({row.get("run_id", "") for row in valid_rows if row.get("run_id")})
    invalid_rows = [row for row in rows if row not in valid_rows]
    models_tested = sorted({f"{provider}:{model}" for provider, model in stats})
    latest_run_ids = valid_run_ids[-6:]

    benchmark_mode_stats = defaultdict(lambda: {"debates": 0, "agent_a_wins": 0, "agent_b_wins": 0, "ties": 0})
    judge_mode_stats = defaultdict(lambda: {"debates": 0, "agent_a_wins": 0, "agent_b_wins": 0, "ties": 0})
    run_stats = defaultdict(lambda: {"valid": 0, "topics": set(), "models": set(), "modes": set(), "judge_modes": set()})
    for row in valid_rows:
        winner = row.get("winner", "")
        for key, buckets in (
            (row.get("benchmark_mode") or "legacy", benchmark_mode_stats),
            (row.get("judge_mode") or "legacy", judge_mode_stats),
        ):
            buckets[key]["debates"] += 1
            if winner == "Agent A":
                buckets[key]["agent_a_wins"] += 1
            elif winner == "Agent B":
                buckets[key]["agent_b_wins"] += 1
            else:
                buckets[key]["ties"] += 1

        run_id = row.get("run_id") or "unknown"
        run_stats[run_id]["valid"] += 1
        run_stats[run_id]["topics"].add(row.get("topic_id") or "unknown")
        run_stats[run_id]["models"].add(f"{provider_label(row.get('position_a_provider', ''), row.get('position_a_model', ''))}:{model_name(row.get('position_a_provider', ''), row.get('position_a_model', ''))}")
        run_stats[run_id]["models"].add(f"{provider_label(row.get('position_b_provider', ''), row.get('position_b_model', ''))}:{model_name(row.get('position_b_provider', ''), row.get('position_b_model', ''))}")
        run_stats[run_id]["modes"].add(row.get("benchmark_mode") or "legacy")
        run_stats[run_id]["judge_modes"].add(row.get("judge_mode") or "legacy")

    lines = [
        "# Model Ranking Summary (All Runs)",
        "",
        f"Generated from {len(valid_rows)} valid judge evaluations across {len(files)} benchmark result files.",
        f"Skipped {len(rows) - len(valid_rows)} rows with judge parse errors, run errors, or missing model fields.",
        f"Models currently tracked: {len(models_tested)}.",
        f"Valid benchmark run IDs included: {len(valid_run_ids)}.",
        "",
        "## Mentor Summary",
        "",
        "| Point | Current Status |",
        "|-------|----------------|",
        "| Proper result storage | CSV/JSON summaries are saved in `results/`; transcripts are saved in `results/conversations/`. |",
        "| Mode 1 single assignment | Implemented as `--benchmark-mode single`; included in the result set. |",
        "| Mode 2 paired role reversal | Implemented as `--benchmark-mode paired`; included in the result set. |",
        "| Position-order bias control | Implemented as `--speaker-order balanced`, which runs both `a_first` and `b_first`. |",
        "| Judge protocols | `winner_only`, `detailed`, and `both` are implemented; one `both` run exposed a malformed detailed JSON response, which is tracked as a parse error. |",
        "| Provider diversity | Academic Cloud and Ollama runs are both included; mixed-provider debates are included. |",
        "| All-runs leaderboard | This file aggregates every `results/*_results.csv` file and labels legacy unprefixed rows as `academic_cloud`. |",
        "",
        "## Key Findings For Discussion",
        "",
        "| Finding | Evidence In Current Runs | Mentor Feedback Needed |",
        "|---------|--------------------------|------------------------|",
        "| Early Position B dominance was probably structural. | Legacy `a_first` rows show Agent B winning most often, while balanced runs are less one-sided. | Should we exclude legacy rows from the final paper leaderboard or keep them as a bias-detection pilot? |",
        "| Academic Cloud models currently outperform local 3B Ollama models. | Academic Cloud has a positive aggregate win rate; Ollama local models mostly lose or tie in mixed runs. | Is this comparison fair, or should local models be benchmarked in a separate tier? |",
        "| Judge mode matters operationally. | `winner_only` is robust; one `detailed` response from Gemma had malformed JSON despite containing a clear winner. | Should detailed judging be retried on parse failure or replaced with stricter JSON-schema enforcement? |",
        "| Some Academic Cloud endpoints are unstable or slow. | `qwen3.5-122b-a10b` and `teuken-7b-instruct-research` produced empty/500 responses; one `devstral`/`glm` run timed out after saving partial results. | Should unreliable endpoints be excluded or reported as reliability metrics? |",
        "| Current sample size is still small. | Rankings are based on prototype smoke tests across a limited number of topics and judges. | How many topics/runs per model pair are enough for mentor-ready conclusions? |",
        "",
        "",
        "## Overall Model Ranking",
        "",
        "| Rank | Model | Provider | Debates | Wins | Losses | Ties | Win Rate | Avg Overall | Avg Factfulness | Avg Groundedness | Avg Confidence |",
        "|------|-------|----------|---------|------|--------|------|----------|-------------|-----------------|------------------|----------------|",
    ]

    for index, item in enumerate(ranking, start=1):
        lines.append(
            f"| {index} | {item['model']} | {item['provider']} | {item['debates']} | {item['wins']} | "
            f"{item['losses']} | {item['ties']} | {item['win_rate']:.2f} | {fmt(item['avg_overall'])} | "
            f"{fmt(item['avg_factfulness'])} | {fmt(item['avg_groundedness'])} | {fmt(item['avg_confidence'])} |"
        )

    provider_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"debates": 0, "wins": 0, "losses": 0, "ties": 0})
    for item in ranking:
        provider_item = provider_stats[item["provider"]]
        provider_item["debates"] += item["debates"]
        provider_item["wins"] += item["wins"]
        provider_item["losses"] += item["losses"]
        provider_item["ties"] += item["ties"]

    lines.extend([
        "",
        "## Per-Provider Summary",
        "",
        "| Provider | Total Debates | Wins | Losses | Ties | Win Rate |",
        "|----------|---------------|------|--------|------|----------|",
    ])
    for provider, item in sorted(provider_stats.items()):
        win_rate = item["wins"] / item["debates"] if item["debates"] else 0
        lines.append(f"| {provider} | {item['debates']} | {item['wins']} | {item['losses']} | {item['ties']} | {win_rate:.2f} |")

    lines.extend([
        "",
        "## Models Tested",
        "",
        "| Model | Provider |",
        "|-------|----------|",
    ])
    for item in ranking:
        lines.append(f"| {item['model']} | {item['provider']} |")

    lines.extend([
        "",
        "## Benchmark Mode Coverage",
        "",
        "| Benchmark Mode | Debates | Agent A Wins | Agent B Wins | Ties |",
        "|----------------|---------|--------------|--------------|------|",
    ])
    for mode, item in sorted(benchmark_mode_stats.items()):
        lines.append(f"| {mode} | {item['debates']} | {item['agent_a_wins']} | {item['agent_b_wins']} | {item['ties']} |")

    lines.extend([
        "",
        "## Judge Mode Coverage",
        "",
        "| Judge Mode | Valid Evaluations | Agent A Wins | Agent B Wins | Ties |",
        "|------------|-------------------|--------------|--------------|------|",
    ])
    for mode, item in sorted(judge_mode_stats.items()):
        lines.append(f"| {mode} | {item['debates']} | {item['agent_a_wins']} | {item['agent_b_wins']} | {item['ties']} |")

    position_stats = defaultdict(lambda: {"debates": 0, "wins": 0})
    speaker_order_stats = defaultdict(lambda: {"debates": 0, "agent_a_wins": 0, "agent_b_wins": 0, "ties": 0})
    for row in valid_rows:
        winner = row.get("winner", "")
        position_stats["Position A"]["debates"] += 1
        position_stats["Position B"]["debates"] += 1
        if winner == "Agent A":
            position_stats["Position A"]["wins"] += 1
        elif winner == "Agent B":
            position_stats["Position B"]["wins"] += 1

        speaker_order = row.get("speaker_order") or "a_first (legacy)"
        speaker_order_stats[speaker_order]["debates"] += 1
        if winner == "Agent A":
            speaker_order_stats[speaker_order]["agent_a_wins"] += 1
        elif winner == "Agent B":
            speaker_order_stats[speaker_order]["agent_b_wins"] += 1
        else:
            speaker_order_stats[speaker_order]["ties"] += 1

    lines.extend([
        "",
        "## Position Win Rates",
        "",
        "| Position | Debates | Wins | Win Rate |",
        "|----------|---------|------|----------|",
    ])
    for position, item in sorted(position_stats.items()):
        win_rate = item["wins"] / item["debates"] if item["debates"] else 0
        lines.append(f"| {position} | {item['debates']} | {item['wins']} | {win_rate:.2f} |")

    lines.extend([
        "",
        "## Speaker Order Effects",
        "",
        "| Speaker Order | Debates | Agent A Wins | Agent B Wins | Ties |",
        "|---------------|---------|--------------|--------------|------|",
    ])
    for speaker_order, item in sorted(speaker_order_stats.items()):
        lines.append(
            f"| {speaker_order} | {item['debates']} | {item['agent_a_wins']} | "
            f"{item['agent_b_wins']} | {item['ties']} |"
        )

    topic_stats = defaultdict(lambda: {"debates": 0, "decisive": 0})
    for row in valid_rows:
        topic = row.get("topic_id") or "unknown"
        topic_stats[topic]["debates"] += 1
        if row.get("winner") != "Tie":
            topic_stats[topic]["decisive"] += 1

    lines.extend([
        "",
        "## Per-Topic Summary",
        "",
        "| Topic | Debates | Decisive Wins |",
        "|-------|---------|---------------|",
    ])
    for topic, item in sorted(topic_stats.items()):
        lines.append(f"| {topic} | {item['debates']} | {item['decisive']} |")

    lines.extend([
        "",
        "## Recent Benchmark Runs",
        "",
        "| Run ID | Valid Evaluations | Topics | Models | Benchmark Modes | Judge Modes |",
        "|--------|-------------------|--------|--------|-----------------|-------------|",
    ])
    for run_id in latest_run_ids:
        item = run_stats[run_id]
        lines.append(
            f"| {run_id} | {item['valid']} | {', '.join(sorted(item['topics']))} | "
            f"{', '.join(sorted(item['models']))} | {', '.join(sorted(item['modes']))} | {', '.join(sorted(item['judge_modes']))} |"
        )

    lines.extend([
        "",
        "## Reliability Notes",
        "",
        "| Issue | Count / Evidence | Handling |",
        "|-------|------------------|----------|",
        f"| Invalid or failed rows | {len(invalid_rows)} rows skipped | Kept in raw CSV/JSON but excluded from win/loss rankings. |",
        "| Malformed detailed judge JSON | Observed in a `judge-mode both` run | Winner-only result remains usable; detailed row is skipped in all-runs ranking. |",
        "| Slow or unstable endpoints | `qwen3.5-122b-a10b`, `teuken-7b-instruct-research`, and a partial `devstral`/`glm` run showed reliability issues | Treat endpoint reliability as a separate experimental observation. |",
        "| Legacy position-order bias | Older rows lack `speaker_order` and default to `a_first (legacy)` | Use balanced speaker-order runs for future conclusions. |",
        "",
        "## Suggested Questions For Mentor",
        "",
        "1. Should the final leaderboard exclude legacy `a_first` pilot rows and use only balanced speaker-order runs?",
        "2. Should Academic Cloud and Ollama/local models be compared in one leaderboard or separate tiers?",
        "3. Should malformed detailed judge outputs be retried automatically with a stricter JSON prompt?",
        "4. How many topics and repeated runs are enough before claiming stable model rankings?",
        "5. Should model reliability failures count as a benchmark metric separate from persuasion quality?",
    ])

    lines.extend([
        "",
        "## Individual Valid Debates",
        "",
        "| Run ID | Topic | Speaker Order | Position A Model | Position B Model | Winner | Confidence |",
        "|--------|-------|---------------|------------------|------------------|--------|------------|",
    ])
    for row in valid_rows:
        position_a_model = model_name(row.get("position_a_provider", ""), row.get("position_a_model", ""))
        position_b_model = model_name(row.get("position_b_provider", ""), row.get("position_b_model", ""))
        position_a_provider = provider_label(row.get("position_a_provider", ""), row.get("position_a_model", ""))
        position_b_provider = provider_label(row.get("position_b_provider", ""), row.get("position_b_model", ""))
        lines.append(
            f"| {row.get('run_id', '')} | {row.get('topic_id', '')} | {row.get('speaker_order') or 'a_first (legacy)'} | "
            f"{position_a_provider}:{position_a_model} | {position_b_provider}:{position_b_model} | "
            f"{row.get('winner', '')} | {row.get('confidence', '')} |"
        )

    return "\n".join(lines) + "\n"


def main() -> None:
    files, rows = read_rows()
    stats, valid_rows = collect_stats(rows)
    report = build_report(files, rows, valid_rows, stats)
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    OUTPUT_PATH.write_text(report, encoding="utf-8")
    ALT_OUTPUT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"Ranking file written to {OUTPUT_PATH}")
    print(f"Alternate copy written to {ALT_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
