import argparse
import csv
import json
import random
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path


JUDGE_RE = re.compile(r"^Judge \d+ \((.+)\) winner$")
TIE = "Tie"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze ideological persuasion by model and judge.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("runs/2026-08-28_ideological_persuasion/dataset"),
    )
    parser.add_argument(
        "--topics",
        type=Path,
        default=Path(
            "runs/2026-08-28_ideological_persuasion/annotation_analysis/validated_ideology_topics.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("runs/2026-08-28_ideological_persuasion/analysis"),
    )
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
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


def detect_judges(rows: list[dict[str, str]]) -> list[str]:
    judges = []
    for field in rows[0]:
        match = JUDGE_RE.match(field)
        if match:
            judges.append(match.group(1))
    return judges


def judge_winner_column(rows: list[dict[str, str]], judge: str) -> str:
    matches = [field for field in rows[0] if field.endswith(f"({judge}) winner")]
    if len(matches) != 1:
        raise ValueError(f"Could not detect winner column for {judge}")
    return matches[0]


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def topic_cluster_bootstrap(
    rows: list[dict[str, object]], samples: int, seed: int = 20260828
) -> tuple[float, float]:
    by_topic: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_topic[str(row["TopicId"])].append(float(row["ConservativeMinusLiberal"]))
    topics = sorted(by_topic)
    randomizer = random.Random(seed)
    estimates = []
    for _ in range(samples):
        sampled = [randomizer.choice(topics) for _ in topics]
        values = [value for topic in sampled for value in by_topic[topic]]
        estimates.append(statistics.mean(values))
    return quantile(estimates, 0.025), quantile(estimates, 0.975)


def markdown_table(rows: list[dict[str, object]], fields: list[tuple[str, str]]) -> str:
    header = "| " + " | ".join(label for _, label in fields) + " |"
    divider = "| " + " | ".join("---:" if index else "---" for index, _ in enumerate(fields)) + " |"
    body = ["| " + " | ".join(str(row[field]) for field, _ in fields) + " |" for row in rows]
    return "\n".join([header, divider, *body])


def main() -> None:
    args = parse_args()
    topics = json.loads(args.topics.read_text(encoding="utf-8"))
    if len(topics) != 20:
        raise ValueError(f"Expected 20 validated topics, found {len(topics)}")
    topic_by_positions = {
        (topic["position_a"].strip(), topic["position_b"].strip()): topic for topic in topics
    }
    raw = read_csv(args.data_dir / "RawDebates.csv")
    diff = read_csv(args.data_dir / "judgements" / "DiffPosJudgements.csv")
    if len(raw) != 480 or len(diff) != 480:
        raise ValueError(f"Expected 480 raw and judgment rows, found raw={len(raw)}, diff={len(diff)}")
    raw_by_id = {row["DebateId"]: row for row in raw}
    if len(raw_by_id) != 480:
        raise ValueError("Raw DebateId values are not unique")
    judges = detect_judges(diff)
    if len(judges) != 3:
        raise ValueError(f"Expected three judges, found {judges}")

    observations: list[dict[str, object]] = []
    judge_position_counts: dict[str, Counter[str]] = {judge: Counter() for judge in judges}
    for judgment in diff:
        raw_row = raw_by_id[judgment["DebateId"]]
        key = (raw_row["positionA"].strip(), raw_row["positionB"].strip())
        if key not in topic_by_positions:
            raise ValueError(f"Could not map debate {raw_row['DebateId']} to a validated topic")
        topic = topic_by_positions[key]
        ideology_by_position = {
            "A": topic["validated_position_a_label"],
            "B": topic["validated_position_b_label"],
        }
        model_position = {
            raw_row["Model1name"]: raw_row["Model1Position"],
            raw_row["Model2name"]: raw_row["Model2Position"],
        }
        for judge in judges:
            winner = judgment[judge_winner_column(diff, judge)]
            if winner not in {raw_row["Model1name"], raw_row["Model2name"], TIE}:
                raise ValueError(f"Invalid winner for debate {raw_row['DebateId']}, judge {judge}")
            winning_ideology = TIE if winner == TIE else ideology_by_position[model_position[winner]]
            judge_position_counts[judge][winning_ideology] += 1
            for model, opponent in (
                (raw_row["Model1name"], raw_row["Model2name"]),
                (raw_row["Model2name"], raw_row["Model1name"]),
            ):
                if winner == TIE:
                    outcome = 0.5
                else:
                    outcome = 1.0 if winner == model else 0.0
                model_slot = "Model1" if model == raw_row["Model1name"] else "Model2"
                observations.append(
                    {
                        "DebateId": raw_row["DebateId"],
                        "TopicId": topic["id"],
                        "Domain": topic["domain"],
                        "Judge": judge,
                        "Model": model,
                        "Opponent": opponent,
                        "Ideology": ideology_by_position[model_position[model]],
                        "TargetStarts": "yes" if raw_row["starting"] == model_slot else "no",
                        "Outcome": outcome,
                    }
                )

    performance_rows = []
    models = sorted({str(row["Model"]) for row in observations})
    for judge_filter in [*judges, "all judges"]:
        for model in models:
            subset = [
                row
                for row in observations
                if row["Model"] == model
                and (judge_filter == "all judges" or row["Judge"] == judge_filter)
            ]
            by_ideology = {
                ideology: [float(row["Outcome"]) for row in subset if row["Ideology"] == ideology]
                for ideology in ("liberal", "conservative")
            }
            liberal_rate = statistics.mean(by_ideology["liberal"])
            conservative_rate = statistics.mean(by_ideology["conservative"])
            performance_rows.append(
                {
                    "Judge": judge_filter,
                    "Model": model,
                    "LiberalEvaluations": len(by_ideology["liberal"]),
                    "LiberalTieAdjustedWinRate": round(liberal_rate, 3),
                    "ConservativeEvaluations": len(by_ideology["conservative"]),
                    "ConservativeTieAdjustedWinRate": round(conservative_rate, 3),
                    "ConservativeMinusLiberal": round(conservative_rate - liberal_rate, 3),
                }
            )

    strata: dict[tuple[str, str, str, str, str], dict[str, float]] = defaultdict(dict)
    for row in observations:
        key = (
            str(row["Judge"]),
            str(row["Model"]),
            str(row["TopicId"]),
            str(row["Opponent"]),
            str(row["TargetStarts"]),
        )
        strata[key][str(row["Ideology"])] = float(row["Outcome"])
    paired_rows = []
    for (judge, model, topic_id, opponent, starts), values in sorted(strata.items()):
        if set(values) != {"liberal", "conservative"}:
            raise ValueError(f"Incomplete matched ideology stratum: {(judge, model, topic_id, opponent, starts)}")
        paired_rows.append(
            {
                "Judge": judge,
                "Model": model,
                "TopicId": topic_id,
                "Opponent": opponent,
                "TargetStarts": starts,
                "LiberalOutcome": values["liberal"],
                "ConservativeOutcome": values["conservative"],
                "ConservativeMinusLiberal": values["conservative"] - values["liberal"],
            }
        )

    paired_summary = []
    for judge_filter in [*judges, "all judges"]:
        for model in models:
            subset = [
                row
                for row in paired_rows
                if row["Model"] == model
                and (judge_filter == "all judges" or row["Judge"] == judge_filter)
            ]
            estimate = statistics.mean(float(row["ConservativeMinusLiberal"]) for row in subset)
            low, high = topic_cluster_bootstrap(subset, args.bootstrap_samples)
            paired_summary.append(
                {
                    "Judge": judge_filter,
                    "Model": model,
                    "MatchedStrata": len(subset),
                    "ConservativeMinusLiberal": round(estimate, 3),
                    "TopicClusterBootstrapLow": round(low, 3),
                    "TopicClusterBootstrapHigh": round(high, 3),
                }
            )

    judge_preference = []
    for judge in judges:
        counts = judge_position_counts[judge]
        decisive = counts["liberal"] + counts["conservative"]
        judge_preference.append(
            {
                "Judge": judge,
                "LiberalWins": counts["liberal"],
                "ConservativeWins": counts["conservative"],
                "Ties": counts[TIE],
                "ConservativeShareDecisive": round(counts["conservative"] / decisive, 3),
            }
        )

    pooled = [row for row in paired_summary if row["Judge"] == "all judges"]
    report = f"""# Ideological Persuasion Experiment

## Design

The experiment uses 20 topics whose opposing positions were validated by three blinded cloud annotators in contemporary U.S. political discourse. Four debating models are crossed over every unordered pair, both model--position assignments, and both starting models, producing 480 eight-message debates. Three cloud judges provide 1,440 verdicts. For each model, liberal and conservative performance is exactly balanced over topic, opponent, starting status, and judge.

## Model-Specific Ideological Performance

The primary estimate is the paired difference between a model's tie-adjusted outcome when defending the conservative position and its outcome when defending the liberal position against the same opponent on the same topic with the same starting status. Positive values indicate stronger observed conservative advocacy; negative values indicate stronger liberal advocacy. Intervals are 95% topic-cluster bootstrap intervals.

{markdown_table(pooled, [('Model', 'Model'), ('MatchedStrata', 'Matched strata'), ('ConservativeMinusLiberal', 'Conservative - liberal'), ('TopicClusterBootstrapLow', '95% low'), ('TopicClusterBootstrapHigh', '95% high')])}

## Judge-Level Ideological Preference

{markdown_table(judge_preference, [('Judge', 'Judge'), ('LiberalWins', 'Liberal wins'), ('ConservativeWins', 'Conservative wins'), ('Ties', 'Ties'), ('ConservativeShareDecisive', 'Conservative share')])}

## Interpretation Boundary

These are LLM-judge preferences under a U.S.-specific ideological annotation scheme. They do not measure human persuasion, model political beliefs, or ideological quality in other political contexts. A model-side difference describes relative advocacy success in this controlled panel, not endorsement of either ideology.
"""

    summary = {
        "design": {
            "topics": len(topics),
            "raw_debates": len(raw),
            "judgment_rows": len(diff),
            "judge_evaluations": len(diff) * len(judges),
            "models": models,
            "judges": judges,
            "paired_strata": len(paired_rows),
        },
        "paired_model_summary": paired_summary,
        "judge_ideological_preference": judge_preference,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "model_ideology_performance.csv", performance_rows)
    write_csv(args.output_dir / "matched_ideology_strata.csv", paired_rows)
    write_csv(args.output_dir / "paired_model_ideology_summary.csv", paired_summary)
    write_csv(args.output_dir / "judge_ideological_preference.csv", judge_preference)
    (args.output_dir / "analysis_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (args.output_dir / "ANALYSIS_REPORT.md").write_text(report, encoding="utf-8")
    print(
        f"Wrote ideological persuasion analysis: debates={len(raw)}, "
        f"judge_evaluations={len(diff) * len(judges)}"
    )


if __name__ == "__main__":
    main()
