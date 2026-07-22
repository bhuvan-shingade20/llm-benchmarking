import argparse
import csv
import glob
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


RESULTS_PATTERN = "results/*_results.csv"
OUTPUT_PATH = Path("results/model_ranking_all_runs.md")
ALT_OUTPUT_PATH = Path("results/all_model_rankings.md")
PROTOCOL_CHART_PATH = Path("results/evaluation_protocol_bump_chart.svg")
VALID_WINNERS = {"Agent A", "Agent B", "Tie"}
MIN_DEBATES_FOR_QUALIFIED_RANKING = 5
PROTOCOL_ORDER = [
    "holistic_persuasion",
    "argument_quality",
    "evidence_fact_check",
    "deliberative_quality",
]
PROTOCOL_LABELS = {
    "holistic_persuasion": "Holistic",
    "argument_quality": "Argument",
    "evidence_fact_check": "Evidence",
    "deliberative_quality": "Deliberative",
    "legacy": "Legacy",
}
PROTOCOL_DESCRIPTIONS = {
    "holistic_persuasion": "Overall neutral-reader persuasiveness.",
    "argument_quality": "Claim-warrant structure, burden of proof, coherence, and rebuttal strength.",
    "evidence_fact_check": "Factfulness, groundedness, and unsupported-claim penalties.",
    "deliberative_quality": "Responsiveness, fair engagement, steelmanning, and intellectual honesty.",
}


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


def model_key(row: dict[str, str], prefix: str) -> tuple[str, str]:
    provider = provider_label(row.get(f"{prefix}_provider", ""), row.get(f"{prefix}_model", ""))
    model = model_name(row.get(f"{prefix}_provider", ""), row.get(f"{prefix}_model", ""))
    return provider, model


def model_label(provider: str, model: str) -> str:
    return f"{provider}:{model}"


def protocol_label(protocol: str) -> str:
    return PROTOCOL_LABELS.get(protocol, protocol)


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


def read_rows(input_glob: str) -> tuple[list[str], list[dict[str, str]]]:
    files = sorted(glob.glob(input_glob))
    rows: list[dict[str, str]] = []
    for path in files:
        with open(path, newline="", encoding="utf-8") as file:
            rows.extend(csv.DictReader(file))
    return files, rows


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def transcript_word_counts(path: str, cache: dict[str, tuple[int, int]]) -> tuple[int, int]:
    if not path:
        return 0, 0
    if path in cache:
        return cache[path]

    transcript_path = Path(path)
    if not transcript_path.exists() or transcript_path.suffix.lower() != ".json":
        cache[path] = (0, 0)
        return cache[path]

    try:
        messages = json.loads(transcript_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        cache[path] = (0, 0)
        return cache[path]

    agent_a_words = 0
    agent_b_words = 0
    if isinstance(messages, list):
        for message in messages:
            if not isinstance(message, dict):
                continue
            speaker = message.get("speaker")
            content = str(message.get("content") or "")
            if speaker == "Agent A":
                agent_a_words += word_count(content)
            elif speaker == "Agent B":
                agent_b_words += word_count(content)
    cache[path] = (agent_a_words, agent_b_words)
    return cache[path]


def is_valid_row(row: dict[str, str]) -> bool:
    winner = row.get("winner", "")
    if winner not in VALID_WINNERS:
        return False
    return bool(row.get("position_a_model") and row.get("position_b_model"))


def row_protocol(row: dict[str, str]) -> str:
    return row.get("evaluation_protocol") or "legacy"


def make_stat_bucket() -> dict[str, Any]:
    return {
        "debates": 0,
        "wins": 0,
        "losses": 0,
        "ties": 0,
        "overall_persuasiveness": [],
        "factfulness": [],
        "groundedness": [],
        "confidence": [],
        "words": [],
    }


def add_participant(bucket: dict[str, Any], row: dict[str, str], prefix: str, won: bool, tied: bool, words: int) -> None:
    confidence = safe_float(row.get("confidence"))
    bucket["debates"] += 1
    if confidence is not None:
        bucket["confidence"].append(confidence)
    if won:
        bucket["wins"] += 1
    elif tied:
        bucket["ties"] += 1
    else:
        bucket["losses"] += 1
    if words:
        bucket["words"].append(float(words))
    for metric_name in ("overall_persuasiveness", "factfulness", "groundedness"):
        value = metric(row, prefix, metric_name)
        if value is not None:
            bucket[metric_name].append(value)


def collect_stats(rows: list[dict[str, str]]) -> dict[str, Any]:
    valid_rows = [row for row in rows if is_valid_row(row)]
    invalid_rows = [row for row in rows if not is_valid_row(row)]
    word_cache: dict[str, tuple[int, int]] = {}

    model_stats: dict[tuple[str, str], dict[str, Any]] = defaultdict(make_stat_bucket)
    protocol_model_stats: dict[str, dict[tuple[str, str], dict[str, Any]]] = defaultdict(lambda: defaultdict(make_stat_bucket))
    balanced_model_stats: dict[tuple[str, str], dict[str, Any]] = defaultdict(make_stat_bucket)
    position_stats = defaultdict(lambda: {"debates": 0, "wins": 0})
    speaker_order_stats = defaultdict(lambda: {"debates": 0, "agent_a_wins": 0, "agent_b_wins": 0, "ties": 0})
    benchmark_mode_stats = defaultdict(lambda: {"debates": 0, "agent_a_wins": 0, "agent_b_wins": 0, "ties": 0})
    judge_mode_stats = defaultdict(lambda: {"debates": 0, "agent_a_wins": 0, "agent_b_wins": 0, "ties": 0})
    protocol_stats = defaultdict(lambda: {"debates": 0, "agent_a_wins": 0, "agent_b_wins": 0, "ties": 0})
    topic_stats = defaultdict(lambda: {"debates": 0, "decisive": 0})
    run_stats = defaultdict(lambda: {"valid": 0, "topics": set(), "models": set(), "modes": set(), "judge_modes": set(), "protocols": set()})

    length_bias = {
        "comparable": 0,
        "longer_won": 0,
        "shorter_won": 0,
        "same_or_tie": 0,
        "winner_words": [],
        "loser_words": [],
        "agent_a_words": [],
        "agent_b_words": [],
        "agent_a_wins_when_longer": 0,
        "agent_b_wins_when_longer": 0,
    }

    for row in valid_rows:
        winner = row.get("winner", "")
        tied = winner == "Tie"
        protocol = row_protocol(row)
        speaker_order = row.get("speaker_order") or "a_first (legacy)"
        benchmark_mode = row.get("benchmark_mode") or "legacy"
        judge_mode = row.get("judge_mode") or "legacy"
        topic = row.get("topic_id") or "unknown"
        run_id = row.get("run_id") or "unknown"
        agent_a_words, agent_b_words = transcript_word_counts(row.get("transcript_json", ""), word_cache)

        participants = [
            ("Position A", "position_a", model_key(row, "position_a"), winner == "Agent A", agent_a_words),
            ("Position B", "position_b", model_key(row, "position_b"), winner == "Agent B", agent_b_words),
        ]

        for position, prefix, key, won, words in participants:
            add_participant(model_stats[key], row, prefix, won, tied, words)
            add_participant(protocol_model_stats[protocol][key], row, prefix, won, tied, words)
            if speaker_order in {"a_first", "b_first"}:
                add_participant(balanced_model_stats[key], row, prefix, won, tied, words)
            position_stats[position]["debates"] += 1
            if won:
                position_stats[position]["wins"] += 1

        for key, buckets in (
            (speaker_order, speaker_order_stats),
            (benchmark_mode, benchmark_mode_stats),
            (judge_mode, judge_mode_stats),
            (protocol, protocol_stats),
        ):
            buckets[key]["debates"] += 1
            if winner == "Agent A":
                buckets[key]["agent_a_wins"] += 1
            elif winner == "Agent B":
                buckets[key]["agent_b_wins"] += 1
            else:
                buckets[key]["ties"] += 1

        topic_stats[topic]["debates"] += 1
        if not tied:
            topic_stats[topic]["decisive"] += 1

        run_stats[run_id]["valid"] += 1
        run_stats[run_id]["topics"].add(topic)
        run_stats[run_id]["models"].add(model_label(*model_key(row, "position_a")))
        run_stats[run_id]["models"].add(model_label(*model_key(row, "position_b")))
        run_stats[run_id]["modes"].add(benchmark_mode)
        run_stats[run_id]["judge_modes"].add(judge_mode)
        run_stats[run_id]["protocols"].add(protocol)

        if agent_a_words and agent_b_words:
            length_bias["comparable"] += 1
            length_bias["agent_a_words"].append(float(agent_a_words))
            length_bias["agent_b_words"].append(float(agent_b_words))
            if winner == "Agent A":
                length_bias["winner_words"].append(float(agent_a_words))
                length_bias["loser_words"].append(float(agent_b_words))
                if agent_a_words > agent_b_words:
                    length_bias["longer_won"] += 1
                    length_bias["agent_a_wins_when_longer"] += 1
                elif agent_a_words < agent_b_words:
                    length_bias["shorter_won"] += 1
                else:
                    length_bias["same_or_tie"] += 1
            elif winner == "Agent B":
                length_bias["winner_words"].append(float(agent_b_words))
                length_bias["loser_words"].append(float(agent_a_words))
                if agent_b_words > agent_a_words:
                    length_bias["longer_won"] += 1
                    length_bias["agent_b_wins_when_longer"] += 1
                elif agent_b_words < agent_a_words:
                    length_bias["shorter_won"] += 1
                else:
                    length_bias["same_or_tie"] += 1
            else:
                length_bias["same_or_tie"] += 1

    return {
        "valid_rows": valid_rows,
        "invalid_rows": invalid_rows,
        "model_stats": model_stats,
        "balanced_model_stats": balanced_model_stats,
        "protocol_model_stats": protocol_model_stats,
        "position_stats": position_stats,
        "speaker_order_stats": speaker_order_stats,
        "benchmark_mode_stats": benchmark_mode_stats,
        "judge_mode_stats": judge_mode_stats,
        "protocol_stats": protocol_stats,
        "topic_stats": topic_stats,
        "run_stats": run_stats,
        "length_bias": length_bias,
    }


def ranking_from_stats(stats: dict[tuple[str, str], dict[str, Any]]) -> list[dict[str, Any]]:
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
                "avg_words": average(item["words"]),
            }
        )
    return sorted(ranking, key=lambda item: (-item["win_rate"], -item["wins"], item["model"]))


def append_ranking_table(lines: list[str], ranking: list[dict[str, Any]], include_status: bool = False) -> None:
    status_column = " | Status" if include_status else ""
    status_separator = "--------|" if include_status else ""
    lines.append(f"| Rank | Model | Provider | Debates | Wins | Losses | Ties | Win Rate | Avg Overall | Avg Factfulness | Avg Groundedness | Avg Confidence{status_column} |")
    lines.append(f"|------|-------|----------|---------|------|--------|------|----------|-------------|-----------------|------------------|----------------|{status_separator}")
    for index, item in enumerate(ranking, start=1):
        status = ""
        if include_status:
            status = "qualified" if item["debates"] >= MIN_DEBATES_FOR_QUALIFIED_RANKING else "preliminary"
            status = f" | {status}"
        lines.append(
            f"| {index} | {item['model']} | {item['provider']} | {item['debates']} | {item['wins']} | "
            f"{item['losses']} | {item['ties']} | {item['win_rate']:.2f} | {fmt(item['avg_overall'])} | "
            f"{fmt(item['avg_factfulness'])} | {fmt(item['avg_groundedness'])} | {fmt(item['avg_confidence'])}{status} |"
        )


def append_group_table(lines: list[str], title: str, name_column: str, groups: dict[str, dict[str, int]]) -> None:
    lines.extend(["", title, "", f"| {name_column} | Debates | Agent A Wins | Agent B Wins | Ties |", "|---|---:|---:|---:|---:|"])
    for name, item in sorted(groups.items()):
        lines.append(f"| {protocol_label(name)} | {item['debates']} | {item['agent_a_wins']} | {item['agent_b_wins']} | {item['ties']} |")


def protocol_rankings(protocol_model_stats: dict[str, dict[tuple[str, str], dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    rankings = {}
    for protocol, stats in protocol_model_stats.items():
        if protocol == "legacy":
            continue
        rankings[protocol] = ranking_from_stats(stats)
    return rankings


def write_protocol_bump_chart(rankings: dict[str, list[dict[str, Any]]], output_path: Path) -> str:
    protocols = [protocol for protocol in PROTOCOL_ORDER if protocol in rankings and rankings[protocol]]
    if len(protocols) < 2:
        svg = """<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"920\" height=\"260\" viewBox=\"0 0 920 260\">
  <rect width=\"920\" height=\"260\" fill=\"#f4f5f0\"/>
  <text x=\"30\" y=\"55\" font-family=\"Arial\" font-size=\"22\" font-weight=\"700\">Evaluation Protocol Bump Chart</text>
  <text x=\"30\" y=\"95\" font-family=\"Arial\" font-size=\"15\">Run `--evaluation-protocol all` to compare model rankings across the four protocols.</text>
</svg>
"""
        output_path.write_text(svg, encoding="utf-8")
        return str(output_path)

    model_set = set()
    rank_lookup: dict[tuple[str, str], int] = {}
    for protocol in protocols:
        for rank, item in enumerate(rankings[protocol], start=1):
            key = model_label(item["provider"], item["model"])
            model_set.add(key)
            rank_lookup[(protocol, key)] = rank

    max_rank = min(10, max(rank_lookup.values()))
    selected_models = sorted(
        model_set,
        key=lambda model: min(rank_lookup.get((protocol, model), 999) for protocol in protocols),
    )[:10]

    width = 1000
    height = 620
    margin_left = 120
    margin_right = 80
    margin_top = 85
    margin_bottom = 85
    x_step = (width - margin_left - margin_right) / max(len(protocols) - 1, 1)
    y_step = (height - margin_top - margin_bottom) / max(max_rank - 1, 1)
    colors = ["#355c7d", "#f28e2b", "#4e4e4e", "#59a14f", "#b07aa1", "#e15759", "#76b7b2", "#edc948", "#9c755f", "#bab0ab"]

    parts = [
        f"<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{width}\" height=\"{height}\" viewBox=\"0 0 {width} {height}\">",
        "<rect width=\"100%\" height=\"100%\" fill=\"#f4f5f0\"/>",
        "<text x=\"30\" y=\"40\" font-family=\"Arial\" font-size=\"22\" font-weight=\"700\">Evaluation Protocol Ranking Bump Chart</text>",
        "<text x=\"30\" y=\"65\" font-family=\"Arial\" font-size=\"13\">Lower rank is better. Lines show how model ranking changes when the judge protocol changes.</text>",
    ]
    for rank in range(1, max_rank + 1):
        y = margin_top + (rank - 1) * y_step
        parts.append(f"<text x=\"55\" y=\"{y + 5:.1f}\" font-family=\"Arial\" font-size=\"12\" fill=\"#555\">{rank}</text>")
        parts.append(f"<line x1=\"{margin_left}\" y1=\"{y:.1f}\" x2=\"{width - margin_right}\" y2=\"{y:.1f}\" stroke=\"#ddd\" stroke-width=\"1\"/>")
    for index, protocol in enumerate(protocols):
        x = margin_left + index * x_step
        parts.append(f"<text x=\"{x:.1f}\" y=\"{height - 35}\" text-anchor=\"middle\" font-family=\"Arial\" font-size=\"13\">{protocol_label(protocol)}</text>")

    for model_index, model in enumerate(selected_models):
        color = colors[model_index % len(colors)]
        points = []
        for index, protocol in enumerate(protocols):
            rank = rank_lookup.get((protocol, model))
            if rank is None or rank > max_rank:
                continue
            x = margin_left + index * x_step
            y = margin_top + (rank - 1) * y_step
            points.append((x, y, rank))
        if len(points) < 2:
            continue
        point_text = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in points)
        parts.append(f"<polyline points=\"{point_text}\" fill=\"none\" stroke=\"{color}\" stroke-width=\"4\" stroke-linejoin=\"round\"/>")
        for x, y, rank in points:
            parts.append(f"<circle cx=\"{x:.1f}\" cy=\"{y:.1f}\" r=\"12\" fill=\"{color}\"/>")
            parts.append(f"<text x=\"{x:.1f}\" y=\"{y + 4:.1f}\" text-anchor=\"middle\" font-family=\"Arial\" font-size=\"10\" fill=\"white\">{rank}</text>")
        last_x, last_y, _ = points[-1]
        safe_model = model.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        parts.append(f"<text x=\"{last_x + 18:.1f}\" y=\"{last_y + 4:.1f}\" font-family=\"Arial\" font-size=\"11\" fill=\"{color}\">{safe_model}</text>")

    parts.append("</svg>")
    output_path.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return str(output_path)


def build_report(files: list[str], rows: list[dict[str, str]], stats: dict[str, Any], chart_path: str) -> str:
    valid_rows = stats["valid_rows"]
    invalid_rows = stats["invalid_rows"]
    overall_ranking = ranking_from_stats(stats["model_stats"])
    qualified_ranking = [item for item in overall_ranking if item["debates"] >= MIN_DEBATES_FOR_QUALIFIED_RANKING]
    preliminary_ranking = [item for item in overall_ranking if item["debates"] < MIN_DEBATES_FOR_QUALIFIED_RANKING]
    balanced_ranking = ranking_from_stats(stats["balanced_model_stats"])
    protocol_ranked = protocol_rankings(stats["protocol_model_stats"])
    valid_run_ids = sorted({row.get("run_id", "") for row in valid_rows if row.get("run_id")})
    latest_run_ids = valid_run_ids[-8:]

    provider_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"debates": 0, "wins": 0, "losses": 0, "ties": 0})
    for item in overall_ranking:
        provider_item = provider_stats[item["provider"]]
        provider_item["debates"] += item["debates"]
        provider_item["wins"] += item["wins"]
        provider_item["losses"] += item["losses"]
        provider_item["ties"] += item["ties"]

    length_bias = stats["length_bias"]
    longer_win_rate = length_bias["longer_won"] / length_bias["comparable"] if length_bias["comparable"] else None

    lines = [
        "# Model Ranking Summary (All Runs)",
        "",
        f"Generated from {len(valid_rows)} valid judge evaluations across {len(files)} benchmark result files.",
        f"Skipped {len(invalid_rows)} rows with judge parse errors, run errors, or missing model fields.",
        f"Headline ranking requires at least {MIN_DEBATES_FOR_QUALIFIED_RANKING} valid debates per model to avoid tiny-sample leaders.",
        f"Evaluation protocol bump chart: `{chart_path}`.",
        "",
        "## Mentor Summary",
        "",
        "| Point | Current Status |",
        "|-------|----------------|",
        "| Four evaluation protocols | Implemented: holistic persuasion, argument quality, evidence/fact-checking, and deliberative quality. Use `--evaluation-protocol all` to judge the same transcript under all four. |",
        "| Protocol comparison graph | Implemented as a bump chart in `results/evaluation_protocol_bump_chart.svg`; x-axis is evaluation protocol, y-axis is model rank. |",
        "| Better model ranking | Headline ranking now filters out models with fewer than 5 valid debates; low-sample models are listed separately as preliminary. |",
        "| Judging bias checks | Report now includes position/order bias and a length-bias diagnostic based on transcript word counts. |",
        "| Balanced position/order control | `--speaker-order balanced` remains the default for benchmark runs. |",
        "| Provider diversity | Academic Cloud and Ollama rows are both included; legacy unprefixed rows are labeled as `academic_cloud`. |",
        "",
        "## Evaluation Protocols",
        "",
        "| Protocol | What It Measures |",
        "|----------|------------------|",
    ]
    for protocol in PROTOCOL_ORDER:
        lines.append(f"| `{protocol}` | {PROTOCOL_DESCRIPTIONS[protocol]} |")

    lines.extend([
        "",
        "## Qualified Model Ranking",
        "",
        f"Models below {MIN_DEBATES_FOR_QUALIFIED_RANKING} valid debates are excluded from this headline table.",
        "",
    ])
    append_ranking_table(lines, qualified_ranking)

    lines.extend([
        "",
        "## Preliminary Low-Sample Models",
        "",
        "These models have promising or poor win rates, but too few debates for a fair leaderboard position.",
        "",
    ])
    append_ranking_table(lines, preliminary_ranking)

    lines.extend([
        "",
        "## Complete Exploratory Ranking",
        "",
        "This includes every valid row and is useful for debugging, but should not be presented as the final fair leaderboard.",
        "",
    ])
    append_ranking_table(lines, overall_ranking, include_status=True)

    lines.extend([
        "",
        "## Balanced-Only Ranking",
        "",
        "Only rows with explicit `speaker_order` equal to `a_first` or `b_first` are included here; legacy one-order rows are excluded.",
        "",
    ])
    append_ranking_table(lines, balanced_ranking, include_status=True)

    lines.extend(["", "## Per-Provider Summary", "", "| Provider | Total Debates | Wins | Losses | Ties | Win Rate |", "|----------|---------------|------|--------|------|----------|"])
    for provider, item in sorted(provider_stats.items()):
        win_rate = item["wins"] / item["debates"] if item["debates"] else 0
        lines.append(f"| {provider} | {item['debates']} | {item['wins']} | {item['losses']} | {item['ties']} | {win_rate:.2f} |")

    append_group_table(lines, "## Benchmark Mode Coverage", "Benchmark Mode", stats["benchmark_mode_stats"])
    append_group_table(lines, "## Judge Mode Coverage", "Judge Mode", stats["judge_mode_stats"])
    append_group_table(lines, "## Evaluation Protocol Coverage", "Evaluation Protocol", stats["protocol_stats"])

    lines.extend(["", "## Protocol-Specific Rankings", ""])
    if protocol_ranked:
        for protocol in [*PROTOCOL_ORDER, *sorted(set(protocol_ranked) - set(PROTOCOL_ORDER))]:
            if protocol not in protocol_ranked:
                continue
            lines.extend([f"### {protocol_label(protocol)}", ""])
            append_ranking_table(lines, protocol_ranked[protocol], include_status=True)
            lines.append("")
    else:
        lines.append("No non-legacy protocol comparison rows yet. Run with `--evaluation-protocol all`.")

    lines.extend([
        "",
        "## Position Win Rates",
        "",
        "| Position | Debates | Wins | Win Rate |",
        "|----------|---------|------|----------|",
    ])
    for position, item in sorted(stats["position_stats"].items()):
        win_rate = item["wins"] / item["debates"] if item["debates"] else 0
        lines.append(f"| {position} | {item['debates']} | {item['wins']} | {win_rate:.2f} |")
    append_group_table(lines, "## Speaker Order Effects", "Speaker Order", stats["speaker_order_stats"])

    lines.extend([
        "",
        "## Judging Bias Diagnostics",
        "",
        "| Bias Check | Result | Interpretation |",
        "|------------|--------|----------------|",
        f"| Length bias | Longer agent won {length_bias['longer_won']} / {length_bias['comparable']} comparable rows ({fmt(longer_win_rate)}) | Values well above 0.50 suggest judges may reward verbosity. |",
        f"| Average winner length | {fmt(average(length_bias['winner_words']))} words | Compare with loser length below. |",
        f"| Average loser length | {fmt(average(length_bias['loser_words']))} words | If winners are much longer, inspect for verbosity bias. |",
        f"| Average Agent A length | {fmt(average(length_bias['agent_a_words']))} words | Helps detect role/order verbosity differences. |",
        f"| Average Agent B length | {fmt(average(length_bias['agent_b_words']))} words | Helps detect role/order verbosity differences. |",
        "| Position/order bias | See `Position Win Rates` and `Speaker Order Effects` above | Legacy rows should not drive final conclusions. |",
    ])

    lines.extend(["", "## Per-Topic Summary", "", "| Topic | Debates | Decisive Wins |", "|-------|---------|---------------|"])
    for topic, item in sorted(stats["topic_stats"].items()):
        lines.append(f"| {topic} | {item['debates']} | {item['decisive']} |")

    lines.extend([
        "",
        "## Recommended Fair Rerun Plan",
        "",
        "Use a fixed model pool and enough topics so every model gets at least 5-6 valid debates under balanced order. Example:",
        "",
        "```powershell",
        "python run_benchmark.py --topic-ids ai_assignments,remote_work,assessment_design --benchmark-mode permutations --models openai:qwen3-30b-a3b-instruct-2507,openai:mistral-large-3-675b-instruct-2512,openai:apertus-70b-instruct-2509,ollama:qwen2.5:3b --judge-model openai:gemma-4-31b-it --judge-mode winner_only --evaluation-protocol all --speaker-order balanced --turns 2 --max-tokens 120 --dry-run",
        "```",
        "",
        "Remove `--dry-run` only after checking the planned judge-evaluation count, because protocols multiply judge calls by four.",
        "",
        "## Questions For Mentor",
        "",
        "1. Should the final leaderboard include only qualified models with at least 5-6 valid debates?",
        "2. Should the paper report the four protocol rankings separately or average them into one meta-ranking?",
        "3. Is the bump chart the right visualization for protocol sensitivity, or should we also add bar charts of win rate by protocol?",
        "4. Should length bias be corrected statistically, or only reported as a diagnostic?",
        "5. Should Academic Cloud and Ollama/local models be separate leaderboards because model size differs greatly?",
        "",
        "## Recent Benchmark Runs",
        "",
        "| Run ID | Valid Evaluations | Topics | Models | Benchmark Modes | Judge Modes | Protocols |",
        "|--------|-------------------|--------|--------|-----------------|-------------|-----------|",
    ])
    for run_id in latest_run_ids:
        item = stats["run_stats"][run_id]
        lines.append(
            f"| {run_id} | {item['valid']} | {', '.join(sorted(item['topics']))} | "
            f"{', '.join(sorted(item['models']))} | {', '.join(sorted(item['modes']))} | "
            f"{', '.join(sorted(item['judge_modes']))} | {', '.join(protocol_label(protocol) for protocol in sorted(item['protocols']))} |"
        )

    lines.extend([
        "",
        "## Reliability Notes",
        "",
        "| Issue | Count / Evidence | Handling |",
        "|-------|------------------|----------|",
        f"| Invalid or failed rows | {len(invalid_rows)} rows skipped | Kept in raw CSV/JSON but excluded from win/loss rankings. |",
        "| Malformed detailed judge JSON | Observed in a `judge-mode both` run | Winner-only result remains usable; detailed row is skipped in all-runs ranking. |",
        "| Slow or unstable endpoints | Some Academic Cloud endpoints returned empty/500 responses or timed out | Treat endpoint reliability as a separate experimental observation. |",
        "| Legacy position-order bias | Older rows lack `speaker_order` and default to `a_first (legacy)` | Use balanced speaker-order runs for future conclusions. |",
        "",
        "## Individual Valid Debates",
        "",
        "| Run ID | Topic | Protocol | Speaker Order | Position A Model | Position B Model | Winner | Confidence |",
        "|--------|-------|----------|---------------|------------------|------------------|--------|------------|",
    ])
    for row in valid_rows:
        lines.append(
            f"| {row.get('run_id', '')} | {row.get('topic_id', '')} | {protocol_label(row_protocol(row))} | "
            f"{row.get('speaker_order') or 'a_first (legacy)'} | {model_label(*model_key(row, 'position_a'))} | "
            f"{model_label(*model_key(row, 'position_b'))} | {row.get('winner', '')} | {row.get('confidence', '')} |"
        )

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate all benchmark CSVs into model rankings and protocol charts.")
    parser.add_argument("--input-glob", default=RESULTS_PATTERN, help="Glob pattern for input *_results.csv files.")
    parser.add_argument("--output-dir", default="results", help="Directory for generated Markdown and SVG reports.")
    parser.add_argument("--output-prefix", default="", help="Optional prefix for generated report filenames.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    prefix = f"{args.output_prefix}_" if args.output_prefix else ""
    output_path = output_dir / f"{prefix}model_ranking_all_runs.md"
    alt_output_path = output_dir / f"{prefix}all_model_rankings.md"
    chart_output_path = output_dir / f"{prefix}evaluation_protocol_bump_chart.svg"

    files, rows = read_rows(args.input_glob)
    stats = collect_stats(rows)
    ranked_protocols = protocol_rankings(stats["protocol_model_stats"])
    output_dir.mkdir(parents=True, exist_ok=True)
    chart_path = write_protocol_bump_chart(ranked_protocols, chart_output_path)
    report = build_report(files, rows, stats, chart_path)
    output_path.write_text(report, encoding="utf-8")
    alt_output_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"Ranking file written to {output_path}")
    print(f"Alternate copy written to {alt_output_path}")
    print(f"Protocol bump chart written to {chart_output_path}")


if __name__ == "__main__":
    main()
