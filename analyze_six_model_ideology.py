import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from generate_judgement_files import read_raw_rows
from run_conversation import parse_model_spec


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze the six-model ideological debate extension.")
    parser.add_argument("--raw", type=Path, default=Path("runs/2026-08-29_six_model_ideology/RawDebates.csv"))
    parser.add_argument("--judgements", type=Path, default=Path("runs/2026-08-29_six_model_ideology/judgements"))
    parser.add_argument("--topics", type=Path, default=Path("topics/ideology_topics.json"))
    parser.add_argument("--config", type=Path, default=Path("configs/extension_2026_08_29.json"))
    parser.add_argument("--allow-incomplete", action="store_true")
    return parser.parse_args()


def bootstrap_topic_difference(frame: pd.DataFrame, seed: int) -> tuple[float, float]:
    topics = frame["TopicId"].unique()
    rng = np.random.default_rng(seed)
    estimates = []
    for _ in range(5000):
        sampled = rng.choice(topics, size=len(topics), replace=True)
        pieces = [frame[frame["TopicId"] == topic] for topic in sampled]
        draw = pd.concat(pieces, ignore_index=True)
        estimates.append(draw["MatchedDifference"].mean())
    return tuple(float(value) for value in np.quantile(estimates, [0.025, 0.975]))


def pct(value: float) -> str:
    return f"{100 * value:.1f}%"


def main() -> None:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    selected_ids = set(config["generated_debates"]["topic_ids"])
    topics = [topic for topic in json.loads(args.topics.read_text(encoding="utf-8")) if topic["id"] in selected_ids]
    if len(topics) != 10:
        raise ValueError(f"Expected 10 frozen topics, found {len(topics)}")
    topic_lookup = {
        (topic["position_a"].strip(), topic["position_b"].strip()): topic for topic in topics
    }

    raw = pd.DataFrame(read_raw_rows(args.raw))
    if len(raw) != 600:
        raise ValueError(f"Expected 600 raw debates, found {len(raw)}")
    raw["TopicId"] = raw.apply(
        lambda row: topic_lookup[(row["positionA"].strip(), row["positionB"].strip())]["id"],
        axis=1,
    )
    raw["PositionALabel"] = raw.apply(
        lambda row: topic_lookup[(row["positionA"].strip(), row["positionB"].strip())]["intended_position_a_label"],
        axis=1,
    )
    raw["PositionBLabel"] = raw.apply(
        lambda row: topic_lookup[(row["positionA"].strip(), row["positionB"].strip())]["intended_position_b_label"],
        axis=1,
    )

    files = sorted(args.judgements.glob("judgements_*.csv"))
    if not files:
        raise ValueError(f"No judgment files found in {args.judgements}")
    judgments = pd.concat([pd.read_csv(path) for path in files], ignore_index=True)
    if judgments.duplicated(["DebateId", "JudgeSpec"]).any():
        raise ValueError("Duplicate generated-debate judgment keys.")
    if not args.allow_incomplete:
        per_judge = judgments.groupby("JudgeSpec").size()
        if len(per_judge) != 6 or not (per_judge == 600).all():
            raise ValueError(f"Expected six 600-row judge streams: {per_judge.to_dict()}")
    merged = judgments.merge(
        raw[
            [
                "DebateId",
                "TopicId",
                "Model1name",
                "Model2name",
                "Model1Position",
                "Model2Position",
                "starting",
                "PositionALabel",
                "PositionBLabel",
            ]
        ],
        on=["DebateId", "Model1name", "Model2name", "Model1Position"],
        suffixes=("", "_Raw"),
    )

    observations = []
    for row in merged.itertuples(index=False):
        for model, position, opponent in (
            (row.Model1name, row.Model1Position, row.Model2name),
            (row.Model2name, row.Model2Position, row.Model1name),
        ):
            label = row.PositionALabel if position == "A" else row.PositionBLabel
            starts = row.starting == ("Model1" if model == row.Model1name else "Model2")
            observations.append(
                {
                    "DebateId": row.DebateId,
                    "TopicId": row.TopicId,
                    "JudgeSpec": row.JudgeSpec,
                    "JudgeDisplayName": row.JudgeDisplayName,
                    "Model": model,
                    "Opponent": opponent,
                    "Ideology": label,
                    "Starts": starts,
                    "Win": int(row.WinnerModel == model),
                }
            )
    observations = pd.DataFrame(observations)
    model_name_to_display = {
        parse_model_spec(model["spec"], "openai").model: model["display_name"]
        for model in config["models"]
    }
    observations["ModelDisplayName"] = observations["Model"].map(model_name_to_display)

    matched = (
        observations.pivot_table(
            index=["TopicId", "JudgeSpec", "Model", "Opponent", "Starts"],
            columns="Ideology",
            values="Win",
            aggfunc="first",
        )
        .dropna(subset=["liberal", "conservative"])
        .reset_index()
    )
    matched["MatchedDifference"] = matched["conservative"] - matched["liberal"]
    summary_rows = []
    for seed, (model, group) in enumerate(observations.groupby("Model"), start=1):
        liberal = group[group["Ideology"] == "liberal"]["Win"].mean()
        conservative = group[group["Ideology"] == "conservative"]["Win"].mean()
        model_matched = matched[matched["Model"] == model]
        low, high = bootstrap_topic_difference(model_matched, seed)
        summary_rows.append(
            {
                "Model": model_name_to_display[model],
                "N": len(group),
                "LiberalWinRate": liberal,
                "ConservativeWinRate": conservative,
                "MatchedConservativeMinusLiberal": model_matched["MatchedDifference"].mean(),
                "CI95Low": low,
                "CI95High": high,
            }
        )
    model_summary = pd.DataFrame(summary_rows).sort_values(
        "MatchedConservativeMinusLiberal", ascending=False
    )
    model_summary.to_csv(args.judgements / "model_ideological_performance.csv", index=False)

    judge_preference = (
        merged.assign(
            WinnerIdeology=lambda frame: np.where(
                frame["WinnerPosition"] == "A", frame["PositionALabel"], frame["PositionBLabel"]
            )
        )
        .groupby("JudgeDisplayName")
        .agg(
            N=("DebateId", "size"),
            ConservativeWinnerRate=("WinnerIdeology", lambda values: (values == "conservative").mean()),
        )
        .reset_index()
        .rename(columns={"JudgeDisplayName": "Judge"})
    )
    judge_preference.to_csv(args.judgements / "judge_ideological_preference.csv", index=False)

    self_rows = []
    for judge_spec, group in merged.groupby("JudgeSpec"):
        judge_model = parse_model_spec(judge_spec, "openai").model
        involved = group[(group["Model1name"] == judge_model) | (group["Model2name"] == judge_model)]
        if involved.empty:
            continue
        self_rate = (involved["WinnerModel"] == judge_model).mean()
        debate_ids = set(involved["DebateId"])
        outside = merged[(merged["DebateId"].isin(debate_ids)) & (merged["JudgeSpec"] != judge_spec)]
        outside_judge_models = outside["JudgeSpec"].map(
            lambda value: parse_model_spec(value, "openai").model
        )
        outside = outside[
            (outside_judge_models != outside["Model1name"])
            & (outside_judge_models != outside["Model2name"])
        ]
        outside_rate = (outside["WinnerModel"] == judge_model).mean()
        self_rows.append(
            {
                "Judge": model_name_to_display[judge_model],
                "InvolvedDebates": len(involved),
                "SelfSelectionRate": self_rate,
                "OtherJudgeSelectionRate": outside_rate,
                "Difference": self_rate - outside_rate,
            }
        )
    self_summary = pd.DataFrame(self_rows)
    self_summary.to_csv(args.judgements / "self_preference.csv", index=False)

    report = [
        "# Six-Model Ideological Persuasion Analysis",
        "",
        "The same six models serve as debaters and forced-choice judges. The factorial "
        "design matches every model's liberal and conservative performances on topic, "
        "opponent, starting status, and judge.",
        "",
        "## Debater performance by assigned ideology",
        "",
        "| Model | Evaluations | Liberal win rate | Conservative win rate | Matched difference | 95% topic-bootstrap interval |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in model_summary.itertuples(index=False):
        report.append(
            f"| {row.Model} | {row.N} | {pct(row.LiberalWinRate)} | "
            f"{pct(row.ConservativeWinRate)} | {pct(row.MatchedConservativeMinusLiberal)} | "
            f"[{pct(row.CI95Low)}, {pct(row.CI95High)}] |"
        )
    report.extend(["", "## Judge ideological preference", "", "| Judge | Evaluations | Conservative-position winner |", "|---|---:|---:|"])
    for row in judge_preference.itertuples(index=False):
        report.append(f"| {row.Judge} | {row.N} | {pct(row.ConservativeWinnerRate)} |")
    report.extend(
        [
            "",
            "These estimates concern assigned advocacy and judge verdicts in the controlled "
            "benchmark. They do not identify a model's private beliefs or imply that the same "
            "labels transfer beyond contemporary U.S. policy discourse.",
        ]
    )
    (args.judgements / "ANALYSIS_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "judgment_rows": len(judgments),
                "judges": int(judgments["JudgeSpec"].nunique()),
                "complete": len(files) == 6 and len(judgments) == 3600,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
