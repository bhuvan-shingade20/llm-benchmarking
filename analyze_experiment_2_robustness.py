import csv
import itertools
import statistics
from collections import Counter, defaultdict
from pathlib import Path


RUN_DIR = Path("runs/2026-09-03_exp2_robustness")


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def pct(value: float) -> str:
    return f"{100 * value:.1f}%"


def main() -> None:
    files = sorted(RUN_DIR.glob("judgements_*.csv"))
    if len(files) != 6:
        raise ValueError(f"Expected six judge streams, found {len(files)}")
    summaries = []
    for path in files:
        rows = read(path)
        if len(rows) != 600:
            raise ValueError(f"Expected 600 rows in {path}, found {len(rows)}")
        grouped = defaultdict(dict)
        for row in rows:
            key = (row["DebateId"], row["Condition"])
            if row["Condition"] in grouped[row["DebateId"]]:
                raise ValueError(f"Duplicate robustness condition {key}")
            grouped[row["DebateId"]][row["Condition"]] = row["WinnerModel"]
        if len(grouped) != 120:
            raise ValueError(f"Expected 120 sampled debates in {path}")
        all_stable = []
        pairwise = []
        reversed_agreement = []
        paraphrase_agreement = []
        any_change = []
        for conditions in grouped.values():
            canonical = [conditions[f"canonical_{index}"] for index in (1, 2, 3)]
            modal = Counter(canonical).most_common(1)[0][0]
            all_stable.append(len(set(canonical)) == 1)
            pairwise.extend(left == right for left, right in itertools.combinations(canonical, 2))
            reversed_agreement.append(conditions["reversed"] == modal)
            paraphrase_agreement.append(conditions["paraphrased"] == modal)
            any_change.append(len(set(conditions.values())) > 1)
        summaries.append(
            {
                "Judge": rows[0]["JudgeSpec"],
                "CanonicalAllThreeStable": statistics.mean(all_stable),
                "CanonicalPairwiseAgreement": statistics.mean(pairwise),
                "OrderInvariantAgreement": statistics.mean(reversed_agreement),
                "ParaphraseAgreement": statistics.mean(paraphrase_agreement),
                "AnyWinnerChange": statistics.mean(any_change),
            }
        )

    output = RUN_DIR / "robustness_summary.csv"
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    report = [
        "# Experiment 2: Robustness and Ablation",
        "",
        "The pre-specified 120-debate sample is balanced across the ten original topics, "
        "model exposure, proposition assignment, and speaking order. Each judge receives "
        "three canonical repetitions, one candidate-order reversal, and one fixed prompt paraphrase.",
        "",
        "| Judge | Three-repeat stability | Pairwise repeat agreement | Order-invariant agreement | Prompt agreement | Any winner change |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in summaries:
        report.append(
            f"| {row['Judge']} | {pct(row['CanonicalAllThreeStable'])} | "
            f"{pct(row['CanonicalPairwiseAgreement'])} | {pct(row['OrderInvariantAgreement'])} | "
            f"{pct(row['ParaphraseAgreement'])} | {pct(row['AnyWinnerChange'])} |"
        )
    (RUN_DIR / "ANALYSIS_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Wrote {output} and {RUN_DIR / 'ANALYSIS_REPORT.md'}")


if __name__ == "__main__":
    main()
