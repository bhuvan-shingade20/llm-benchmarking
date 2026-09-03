import csv
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path("runs")
EXP1 = ROOT / "2026-09-03_exp1_replication"
EXP2 = ROOT / "2026-09-03_exp2_robustness"
EXP3 = ROOT / "2026-09-03_exp3_political_alignment"
EXP4 = ROOT / "2026-08-29_real_world_forced_choice_v2"


def read(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def files(folder: Path) -> list[Path]:
    return sorted(folder.glob("judgements_*.csv"))


def unique(rows: list[dict[str, str]], fields: tuple[str, ...]) -> bool:
    keys = [tuple(row[field] for field in fields) for row in rows]
    return len(keys) == len(set(keys))


def winner_valid(rows: list[dict[str, str]]) -> bool:
    return all(
        row.get("WinnerModel") in {row.get("Model1name"), row.get("Model2name")}
        for row in rows
    )


def exp1_status() -> dict[str, object]:
    raw = read(EXP1 / "RawDebates.csv")
    diff = {path.stem: read(path) for path in files(EXP1 / "different_position")}
    same = {path.stem: read(path) for path in files(EXP1 / "same_position")}
    manifest = read(EXP1 / "same_position" / "same_position_manifest.csv")
    manifest_valid = all(
        row["FixedOpponent"] not in {row["Candidate1Model"], row["Candidate2Model"]}
        and row["CandidateStarts"] in {"yes", "no"}
        and row["TestedPosition"] in {"A", "B"}
        for row in manifest
    )
    return {
        "raw_debates": len(raw),
        "raw_unique": unique(raw, ("DebateId",)) if raw else True,
        "transcripts": len(list((EXP1 / "transcripts").glob("debate_*.json"))),
        "different_position_counts": {key: len(value) for key, value in diff.items()},
        "different_position_valid": all(
            unique(rows, ("DebateId",)) and winner_valid(rows) for rows in diff.values()
        ),
        "same_position_manifest": len(manifest),
        "same_position_manifest_valid": manifest_valid,
        "same_position_counts": {key: len(value) for key, value in same.items()},
        "same_position_valid": all(
            unique(rows, ("ComparisonId",))
            and all(row["WinnerModel"] in {row["Candidate1Model"], row["Candidate2Model"]} for row in rows)
            for rows in same.values()
        ),
        "analysis_exists": (EXP1 / "ANALYSIS_REPORT.md").exists(),
        "complete": len(raw) == 840
        and len(diff) == 6
        and all(len(rows) == 840 for rows in diff.values())
        and len(manifest) == 840
        and manifest_valid
        and len(same) == 6
        and all(len(rows) == 840 for rows in same.values())
        and (EXP1 / "ANALYSIS_REPORT.md").exists(),
    }


def exp2_status() -> dict[str, object]:
    streams = {path.stem: read(path) for path in files(EXP2)}
    condition_counts = {
        key: dict(Counter(row["Condition"] for row in rows)) for key, rows in streams.items()
    }
    valid = all(
        unique(rows, ("DebateId", "Condition"))
        and set(Counter(row["Condition"] for row in rows)).issubset(
            {"canonical_1", "canonical_2", "canonical_3", "reversed", "paraphrased"}
        )
        for rows in streams.values()
    )
    return {
        "stream_counts": {key: len(value) for key, value in streams.items()},
        "condition_counts": condition_counts,
        "valid": valid,
        "analysis_exists": (EXP2 / "ANALYSIS_REPORT.md").exists(),
        "complete": len(streams) == 6
        and valid
        and all(len(rows) == 600 for rows in streams.values())
        and (EXP2 / "ANALYSIS_REPORT.md").exists(),
    }


def exp3_status() -> dict[str, object]:
    annotation_rows = [row for path in sorted((EXP3 / "annotations").glob("annotations_*.csv")) for row in read(path)]
    raw = read(EXP3 / "RawDebates.csv")
    streams = {path.stem: read(path) for path in files(EXP3 / "judgements")}
    summary_path = EXP3 / "annotation_analysis" / "analysis_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    valid = all(unique(rows, ("DebateId",)) and winner_valid(rows) for rows in streams.values())
    return {
        "annotation_rows": len(annotation_rows),
        "annotation_unique": unique(annotation_rows, ("TopicId", "Annotator")) if annotation_rows else True,
        "accepted_topics": summary.get("accepted_topics", 0),
        "raw_debates": len(raw),
        "judge_counts": {key: len(value) for key, value in streams.items()},
        "valid": valid,
        "analysis_exists": (EXP3 / "judgements" / "ANALYSIS_REPORT.md").exists(),
        "complete": len(annotation_rows) == 30
        and summary.get("accepted_topics") == 10
        and len(raw) == 600
        and len(streams) == 6
        and valid
        and all(len(rows) == 600 for rows in streams.values())
        and (EXP3 / "judgements" / "ANALYSIS_REPORT.md").exists(),
    }


def exp4_status() -> dict[str, object]:
    streams = {path.stem: read(path) for path in files(EXP4)}
    primary = {
        key: [
            row
            for row in rows
            if row["PromptVersion"] == "canonical"
            and row["PresentationOrder"] == "pro_first"
            and row["RepeatIndex"] == "1"
        ]
        for key, rows in streams.items()
    }
    valid = all(
        unique(rows, ("DebateId",))
        and all(row["WinnerSide"] in {"Pro", "Con"} for row in rows)
        for rows in primary.values()
    )
    return {
        "primary_counts": {key: len(value) for key, value in primary.items()},
        "valid": valid,
        "analysis_exists": (EXP4 / "judge_human_agreement.csv").exists(),
        "complete": len(primary) == 6
        and valid
        and all(len(rows) == 740 for rows in primary.values())
        and (EXP4 / "judge_human_agreement.csv").exists(),
    }


def main() -> None:
    report = {
        "experiment_1": exp1_status(),
        "experiment_2": exp2_status(),
        "experiment_3": exp3_status(),
        "experiment_4": exp4_status(),
    }
    report["all_complete"] = all(report[key]["complete"] for key in report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
