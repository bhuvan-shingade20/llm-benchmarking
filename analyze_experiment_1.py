import csv
import itertools
import json
from pathlib import Path

import pandas as pd

from generate_judgement_files import read_raw_rows
from run_conversation import parse_model_spec


CONFIG = Path("configs/experiment_1_replication_2026_09_03.json")
RUN_DIR = Path("runs/2026-09-03_exp1_replication")


def read_judgements(folder: Path) -> pd.DataFrame:
    files = sorted(folder.glob("judgements_*.csv"))
    if len(files) != 6:
        raise ValueError(f"Expected six judge streams in {folder}, found {len(files)}")
    frames = [pd.read_csv(path) for path in files]
    if any(len(frame) != 840 for frame in frames):
        raise ValueError(f"Every judge stream in {folder} must contain 840 rows")
    return pd.concat(frames, ignore_index=True)


def ranking_rows(frame: pd.DataFrame, mode: str, display: dict[str, str]) -> pd.DataFrame:
    observations = []
    candidate_fields = (
        ("Model1name", "Model2name")
        if mode == "different_position"
        else ("Candidate1Model", "Candidate2Model")
    )
    for row in frame.itertuples(index=False):
        left = getattr(row, candidate_fields[0])
        right = getattr(row, candidate_fields[1])
        for model in (left, right):
            observations.append(
                {
                    "Mode": mode,
                    "JudgeSpec": row.JudgeSpec,
                    "Model": model,
                    "Win": int(row.WinnerModel == model),
                }
            )
    observations = pd.DataFrame(observations)
    summary = (
        observations.groupby(["Mode", "JudgeSpec", "Model"])
        .agg(Evaluations=("Win", "size"), WinRate=("Win", "mean"))
        .reset_index()
    )
    summary["Rank"] = summary.groupby(["Mode", "JudgeSpec"])["WinRate"].rank(
        ascending=False, method="average"
    )
    summary["ModelDisplayName"] = summary["Model"].map(display)
    return summary


def agreement(frame: pd.DataFrame, key: str, mode: str) -> list[dict[str, object]]:
    pivot = frame.pivot(index=key, columns="JudgeSpec", values="WinnerModel")
    output = []
    for left, right in itertools.combinations(pivot.columns, 2):
        valid = pivot[[left, right]].dropna()
        output.append(
            {
                "Mode": mode,
                "Judge1": left,
                "Judge2": right,
                "Comparisons": len(valid),
                "Agreement": (valid[left] == valid[right]).mean(),
            }
        )
    return output


def pct(value: float) -> str:
    return f"{100 * value:.1f}%"


def main() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    display = {
        parse_model_spec(model["spec"], "openai").model: model["display_name"]
        for model in config["models"]
    }
    raw = pd.DataFrame(read_raw_rows(RUN_DIR / "RawDebates.csv"))
    if len(raw) != 840 or raw["DebateId"].duplicated().any():
        raise ValueError("Experiment 1 requires 840 unique raw debates")
    diff = read_judgements(RUN_DIR / "different_position")
    same = read_judgements(RUN_DIR / "same_position")
    raw["DebateId"] = raw["DebateId"].astype(str)
    diff["DebateId"] = diff["DebateId"].astype(str)
    same["ComparisonId"] = same["ComparisonId"].astype(str)
    if diff.duplicated(["DebateId", "JudgeSpec"]).any():
        raise ValueError("Duplicate different-position judgment key")
    if same.duplicated(["ComparisonId", "JudgeSpec"]).any():
        raise ValueError("Duplicate same-position judgment key")

    rankings = pd.concat(
        [
            ranking_rows(diff, "different_position", display),
            ranking_rows(same, "same_position", display),
        ],
        ignore_index=True,
    )
    rankings.to_csv(RUN_DIR / "rankings_by_judge_and_mode.csv", index=False)
    averaged = (
        rankings.groupby(["Mode", "Model", "ModelDisplayName"])
        .agg(MeanRank=("Rank", "mean"), MeanWinRate=("WinRate", "mean"))
        .reset_index()
        .sort_values(["Mode", "MeanRank", "ModelDisplayName"])
    )
    averaged.to_csv(RUN_DIR / "rankings_averaged.csv", index=False)

    agreement_rows = agreement(diff, "DebateId", "different_position") + agreement(
        same, "ComparisonId", "same_position"
    )
    pd.DataFrame(agreement_rows).to_csv(RUN_DIR / "interjudge_agreement.csv", index=False)

    topics = json.loads(Path(config["generated_debates"]["topics_file"]).read_text(encoding="utf-8"))
    topic_lookup = {(topic["position_a"], topic["position_b"]): topic for topic in topics}
    raw["TopicId"] = raw.apply(
        lambda row: topic_lookup[(row["positionA"], row["positionB"])]["id"], axis=1
    )
    raw["ExpectedEasierPosition"] = raw.apply(
        lambda row: topic_lookup[(row["positionA"], row["positionB"])].get("expected_easier_position"),
        axis=1,
    )
    controls = diff.merge(
        raw[["DebateId", "TopicId", "ExpectedEasierPosition"]], on="DebateId", how="left"
    )
    controls = controls[controls["ExpectedEasierPosition"].notna()].copy()
    controls["ExpectedWinnerSelected"] = controls["WinnerPosition"] == controls["ExpectedEasierPosition"]
    control_summary = (
        controls.groupby(["TopicId", "JudgeDisplayName"])
        .agg(Evaluations=("DebateId", "size"), ExpectedWinnerRate=("ExpectedWinnerSelected", "mean"))
        .reset_index()
    )
    control_summary.to_csv(RUN_DIR / "extreme_control_recovery.csv", index=False)

    report = [
        "# Experiment 1: Extended Replication",
        "",
        "All judgments are forced choices, and the same six models serve as debaters and judges. "
        "Different-position and fixed-opponent same-position rankings are reported separately.",
        "",
        "## Rankings averaged across judges",
        "",
        "| Mode | Model | Mean rank | Mean win rate |",
        "|---|---|---:|---:|",
    ]
    for row in averaged.itertuples(index=False):
        report.append(
            f"| {row.Mode.replace('_', ' ')} | {row.ModelDisplayName} | "
            f"{row.MeanRank:.2f} | {pct(row.MeanWinRate)} |"
        )
    report.extend(
        [
            "",
            "## Extreme-control recovery",
            "",
            "| Topic | Judge | Evaluations | Expected easier position selected |",
            "|---|---|---:|---:|",
        ]
    )
    for row in control_summary.itertuples(index=False):
        report.append(
            f"| {row.TopicId} | {row.JudgeDisplayName} | {row.Evaluations} | "
            f"{pct(row.ExpectedWinnerRate)} |"
        )
    (RUN_DIR / "ANALYSIS_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Wrote Experiment 1 analysis to {RUN_DIR}")


if __name__ == "__main__":
    main()
