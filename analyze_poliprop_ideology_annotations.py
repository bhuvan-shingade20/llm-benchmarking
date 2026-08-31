import argparse
import csv
import json
from collections import Counter
from pathlib import Path


DEFAULT_PREPARED = Path("data/external/poliprop/PoliPropPrepared.jsonl")
DEFAULT_INPUT_DIR = Path("runs/2026-08-29_poliprop_ideology_annotations")
DEFAULT_OUTPUT = Path("runs/2026-08-29_poliprop_ideology_annotations/ideology_consensus.csv")

FIELDS = [
    "DebateId",
    "AnnotationCount",
    "RelevantVotes",
    "Accepted",
    "ProConsensusScore",
    "ConConsensusScore",
    "LiberalSide",
    "ConservativeSide",
    "ExactScoreAgreement",
    "SignAgreement",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate blinded PoliProp ideology annotations.")
    parser.add_argument("--prepared", type=Path, default=DEFAULT_PREPARED)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--allow-incomplete", action="store_true")
    return parser.parse_args()


def median(values: list[int]) -> int:
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def sign(value: int) -> int:
    return (value > 0) - (value < 0)


def main() -> None:
    args = parse_args()
    prepared = [json.loads(line) for line in args.prepared.read_text(encoding="utf-8").splitlines()]
    debate_ids = {int(row["debate_id"]) for row in prepared}
    annotations: list[dict[str, str]] = []
    files = sorted(args.input_dir.glob("annotations_*.csv"))
    for path in files:
        with path.open(newline="", encoding="utf-8") as handle:
            annotations.extend(csv.DictReader(handle))
    grouped: dict[int, list[dict[str, str]]] = {debate_id: [] for debate_id in debate_ids}
    for row in annotations:
        debate_id = int(row["DebateId"])
        if debate_id not in grouped:
            raise ValueError(f"Unknown debate id in annotations: {debate_id}")
        grouped[debate_id].append(row)
    if not args.allow_incomplete:
        bad = {debate_id: len(rows) for debate_id, rows in grouped.items() if len(rows) != 3}
        if bad:
            raise ValueError(f"Expected three annotations per debate; incomplete={len(bad)}")

    output_rows = []
    for debate_id in sorted(grouped):
        rows = grouped[debate_id]
        pro_scores = [int(row["ProScore"]) for row in rows]
        con_scores = [int(row["ConScore"]) for row in rows]
        relevant_votes = sum(int(row["PoliticallyRelevant"]) for row in rows)
        pro_consensus = median(pro_scores) if rows else 0
        con_consensus = median(con_scores) if rows else 0
        accepted = (
            len(rows) == 3
            and relevant_votes >= 2
            and sign(pro_consensus) != 0
            and sign(con_consensus) != 0
            and sign(pro_consensus) == -sign(con_consensus)
        )
        liberal_side = ""
        conservative_side = ""
        if accepted:
            liberal_side = "Pro" if pro_consensus < 0 else "Con"
            conservative_side = "Con" if liberal_side == "Pro" else "Pro"
        output_rows.append(
            {
                "DebateId": debate_id,
                "AnnotationCount": len(rows),
                "RelevantVotes": relevant_votes,
                "Accepted": int(accepted),
                "ProConsensusScore": pro_consensus,
                "ConConsensusScore": con_consensus,
                "LiberalSide": liberal_side,
                "ConservativeSide": conservative_side,
                "ExactScoreAgreement": int(
                    len(rows) == 3
                    and len(set(pro_scores)) == 1
                    and len(set(con_scores)) == 1
                ),
                "SignAgreement": int(
                    len(rows) == 3
                    and len({sign(value) for value in pro_scores}) == 1
                    and len({sign(value) for value in con_scores}) == 1
                ),
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(output_rows)
    accepted_rows = [row for row in output_rows if row["Accepted"]]
    summary = {
        "annotation_files": len(files),
        "annotation_rows": len(annotations),
        "complete_debates": sum(row["AnnotationCount"] == 3 for row in output_rows),
        "accepted_ideological_debates": len(accepted_rows),
        "accepted_conservative_side": dict(
            Counter(row["ConservativeSide"] for row in accepted_rows)
        ),
        "exact_score_agreement": sum(row["ExactScoreAgreement"] for row in output_rows),
        "sign_agreement": sum(row["SignAgreement"] for row in output_rows),
    }
    (args.output.parent / "ideology_annotation_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
