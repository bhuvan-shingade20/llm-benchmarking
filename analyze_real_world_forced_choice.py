import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_RESULTS = Path("runs/2026-08-29_real_world_forced_choice_v2")
DEFAULT_IDEOLOGY = Path(
    "runs/2026-08-29_poliprop_ideology_annotations/ideology_consensus.csv"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze real-world forced-choice judgments.")
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--ideology", type=Path, default=DEFAULT_IDEOLOGY)
    parser.add_argument("--allow-incomplete", action="store_true")
    return parser.parse_args()


def interval(values: pd.Series, seed: int) -> tuple[float, float]:
    array = values.to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    means = np.empty(5000)
    for index in range(len(means)):
        means[index] = rng.choice(array, size=len(array), replace=True).mean()
    low, high = np.quantile(means, [0.025, 0.975])
    return float(low), float(high)


def pct(value: float) -> str:
    return f"{100 * value:.1f}%"


def main() -> None:
    args = parse_args()
    files = sorted(args.results_dir.glob("judgements_*.csv"))
    if not files:
        raise ValueError(f"No judgment files found in {args.results_dir}")
    frames = [pd.read_csv(path) for path in files]
    results = pd.concat(frames, ignore_index=True)
    key = ["DebateId", "JudgeSpec", "PromptVersion", "PresentationOrder", "RepeatIndex"]
    if results.duplicated(key).any():
        raise ValueError("Duplicate judgment keys detected.")
    if not set(results["WinnerSide"]).issubset({"Pro", "Con"}):
        raise ValueError("Forced-choice results contain an invalid or tied winner.")
    if not args.allow_incomplete:
        per_judge = results.groupby("JudgeSpec").size()
        if len(per_judge) != 6 or not (per_judge == 1220).all():
            raise ValueError(f"Expected six complete 1,220-row judge streams: {per_judge.to_dict()}")

    baseline = results[
        (results["PromptVersion"] == "canonical")
        & (results["PresentationOrder"] == "pro_first")
        & (results["RepeatIndex"] == 1)
    ].copy()
    baseline["HumanAgreement"] = baseline["HumanAgreement"].astype(int)

    judge_rows = []
    for seed, (judge, group) in enumerate(baseline.groupby("JudgeDisplayName"), start=1):
        low, high = interval(group["HumanAgreement"], seed)
        judge_rows.append(
            {
                "Judge": judge,
                "N": len(group),
                "HumanAgreement": group["HumanAgreement"].mean(),
                "CI95Low": low,
                "CI95High": high,
                "ProSelectionRate": (group["WinnerSide"] == "Pro").mean(),
            }
        )
    judge_summary = pd.DataFrame(judge_rows).sort_values("HumanAgreement", ascending=False)
    judge_summary.to_csv(args.results_dir / "judge_human_agreement.csv", index=False)

    pivot = baseline.pivot(index="DebateId", columns="JudgeDisplayName", values="WinnerSide")
    pairwise_rows = []
    for left, right in itertools.combinations(pivot.columns, 2):
        valid = pivot[[left, right]].dropna()
        pairwise_rows.append(
            {
                "Judge1": left,
                "Judge2": right,
                "N": len(valid),
                "Agreement": (valid[left] == valid[right]).mean(),
            }
        )
    pd.DataFrame(pairwise_rows).to_csv(
        args.results_dir / "interjudge_agreement.csv", index=False
    )

    sample = results[results["RobustnessSample"].astype(int) == 1].copy()
    repeat = sample[
        (sample["PromptVersion"] == "canonical")
        & (sample["PresentationOrder"] == "pro_first")
        & (sample["RepeatIndex"].isin([1, 2, 3]))
    ]
    repeat_rows = []
    for judge, group in repeat.groupby("JudgeDisplayName"):
        repeat_pivot = group.pivot(index="DebateId", columns="RepeatIndex", values="WinnerSide")
        repeat_pivot = repeat_pivot.dropna()
        comparisons = [
            (repeat_pivot[left] == repeat_pivot[right]).mean()
            for left, right in ((1, 2), (1, 3), (2, 3))
        ]
        repeat_rows.append(
            {
                "Judge": judge,
                "N": len(repeat_pivot),
                "AllThreeStable": repeat_pivot.nunique(axis=1).eq(1).mean(),
                "MeanPairwiseAgreement": float(np.mean(comparisons)),
            }
        )
    repeat_summary = pd.DataFrame(repeat_rows)
    repeat_summary.to_csv(args.results_dir / "repeat_stability.csv", index=False)

    canonical_one = sample[
        (sample["PromptVersion"] == "canonical")
        & (sample["PresentationOrder"] == "pro_first")
        & (sample["RepeatIndex"] == 1)
    ][["DebateId", "JudgeDisplayName", "WinnerSide", "WinnerCandidate"]]
    reversed_one = sample[
        (sample["PromptVersion"] == "canonical")
        & (sample["PresentationOrder"] == "con_first")
        & (sample["RepeatIndex"] == 1)
    ][["DebateId", "JudgeDisplayName", "WinnerSide", "WinnerCandidate"]]
    order_pairs = canonical_one.merge(
        reversed_one,
        on=["DebateId", "JudgeDisplayName"],
        suffixes=("_Original", "_Reversed"),
    )
    order_summary = (
        order_pairs.assign(
            Stable=lambda frame: frame["WinnerSide_Original"] == frame["WinnerSide_Reversed"],
            Candidate1Original=lambda frame: frame["WinnerCandidate_Original"] == "Candidate 1",
            Candidate1Reversed=lambda frame: frame["WinnerCandidate_Reversed"] == "Candidate 1",
        )
        .groupby("JudgeDisplayName")
        .agg(
            N=("DebateId", "size"),
            SideAgreement=("Stable", "mean"),
            Candidate1Original=("Candidate1Original", "mean"),
            Candidate1Reversed=("Candidate1Reversed", "mean"),
        )
        .reset_index()
        .rename(columns={"JudgeDisplayName": "Judge"})
    )
    order_summary.to_csv(args.results_dir / "presentation_order_robustness.csv", index=False)

    repeat_modal = (
        repeat.groupby(["DebateId", "JudgeDisplayName"])["WinnerSide"]
        .agg(lambda values: values.value_counts().index[0])
        .rename("CanonicalModal")
        .reset_index()
    )
    paraphrase = sample[
        (sample["PromptVersion"] == "paraphrase")
        & (sample["PresentationOrder"] == "pro_first")
        & (sample["RepeatIndex"] == 1)
    ][["DebateId", "JudgeDisplayName", "WinnerSide"]].rename(
        columns={"WinnerSide": "ParaphraseWinner"}
    )
    prompt_pairs = repeat_modal.merge(paraphrase, on=["DebateId", "JudgeDisplayName"])
    prompt_summary = (
        prompt_pairs.assign(
            Stable=lambda frame: frame["CanonicalModal"] == frame["ParaphraseWinner"]
        )
        .groupby("JudgeDisplayName")
        .agg(N=("DebateId", "size"), Agreement=("Stable", "mean"))
        .reset_index()
        .rename(columns={"JudgeDisplayName": "Judge"})
    )
    prompt_summary.to_csv(args.results_dir / "prompt_robustness.csv", index=False)

    ideology_summary = pd.DataFrame()
    if args.ideology.exists():
        ideology = pd.read_csv(args.ideology)
        ideology = ideology[ideology["Accepted"].astype(int) == 1]
        ideological = baseline.merge(ideology, on="DebateId")
        ideological["SelectedConservative"] = (
            ideological["WinnerSide"] == ideological["ConservativeSide"]
        )
        ideological["HumanWinnerIdeology"] = np.where(
            ideological["HumanMajority"] == ideological["ConservativeSide"],
            "Conservative",
            "Liberal",
        )
        ideology_summary = (
            ideological.groupby("JudgeDisplayName")
            .agg(
                N=("DebateId", "size"),
                ConservativeSelectionRate=("SelectedConservative", "mean"),
                HumanAgreement=("HumanAgreement", "mean"),
            )
            .reset_index()
            .rename(columns={"JudgeDisplayName": "Judge"})
        )
        conditional = (
            ideological.groupby(["JudgeDisplayName", "HumanWinnerIdeology"])[
                "HumanAgreement"
            ]
            .mean()
            .unstack()
            .reset_index()
            .rename(columns={"JudgeDisplayName": "Judge"})
        )
        ideology_summary = ideology_summary.merge(conditional, on="Judge", how="left")
        ideology_summary.to_csv(args.results_dir / "ideological_preference.csv", index=False)

    report = [
        "# Real-World Forced-Choice Evaluation",
        "",
        "This report evaluates the frozen six-model panel on human-written PoliProp debates. "
        "All model verdicts are forced choices; the primary benchmark includes only debates "
        "with a decisive released human-majority label.",
        "",
        "## Human-majority agreement",
        "",
        "| Judge | N | Agreement | 95% bootstrap interval | Pro selected |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in judge_summary.itertuples(index=False):
        report.append(
            f"| {row.Judge} | {row.N} | {pct(row.HumanAgreement)} | "
            f"[{pct(row.CI95Low)}, {pct(row.CI95High)}] | {pct(row.ProSelectionRate)} |"
        )
    report.extend(["", "## Repeated-judgment stability", "", "| Judge | N | All three stable | Mean pairwise agreement |", "|---|---:|---:|---:|"])
    for row in repeat_summary.itertuples(index=False):
        report.append(f"| {row.Judge} | {row.N} | {pct(row.AllThreeStable)} | {pct(row.MeanPairwiseAgreement)} |")
    report.extend(["", "## Candidate-order robustness", "", "| Judge | N | Same side after reversal | Candidate 1, original | Candidate 1, reversed |", "|---|---:|---:|---:|---:|"])
    for row in order_summary.itertuples(index=False):
        report.append(f"| {row.Judge} | {row.N} | {pct(row.SideAgreement)} | {pct(row.Candidate1Original)} | {pct(row.Candidate1Reversed)} |")
    report.extend(["", "## Prompt-phrasing robustness", "", "| Judge | N | Agreement with canonical modal verdict |", "|---|---:|---:|"])
    for row in prompt_summary.itertuples(index=False):
        report.append(f"| {row.Judge} | {row.N} | {pct(row.Agreement)} |")
    if not ideology_summary.empty:
        report.extend(["", "## Ideological preference diagnostic", "", "| Judge | N | Conservative selected | Human agreement | Agreement when human winner is liberal | Agreement when human winner is conservative |", "|---|---:|---:|---:|---:|---:|"])
        for row in ideology_summary.itertuples(index=False):
            report.append(f"| {row.Judge} | {row.N} | {pct(row.ConservativeSelectionRate)} | {pct(row.HumanAgreement)} | {pct(row.Liberal)} | {pct(row.Conservative)} |")
    report.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "Human-majority agreement is external validation against Debate.org voters, not "
            "a universal ground truth for persuasion. Ideological results describe verdict "
            "patterns under the stated U.S. policy annotation frame; they do not establish "
            "a model's political beliefs.",
        ]
    )
    (args.results_dir / "ANALYSIS_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    summary = {
        "result_rows": len(results),
        "judges": int(results["JudgeSpec"].nunique()),
        "primary_rows": len(baseline),
        "complete": len(files) == 6 and all(len(frame) == 1220 for frame in frames),
    }
    (args.results_dir / "analysis_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
