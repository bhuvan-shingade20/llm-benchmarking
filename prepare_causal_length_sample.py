import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from analyze_curated_datasets import parse_turns, word_count


CONFIG = Path("configs/experiment_2b_causal_length_report_2026_09_04.json")
MANIFEST = Path("data/experiment_manifests/causal_length_report_sample_2026_09_04.csv")
FIELDS = [
    "ProtocolVersion",
    "DebateId",
    "TopicId",
    "FocalCandidate",
    "OpponentCandidate",
    "FocalModel",
    "OpponentModel",
    "FocalPosition",
    "FocalStarted",
    "InterventionDirection",
    "FocalWordsOriginal",
    "OpponentWords",
    "RelativeLengthGap",
    "TargetWords",
    "PresentationOrder",
    "SourceSha256",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def topic_lookup(path: Path) -> dict[tuple[str, str], str]:
    topics = json.loads(path.read_text(encoding="utf-8"))
    return {(topic["position_a"], topic["position_b"]): topic["id"] for topic in topics}


def candidate_metadata(row: dict[str, str], candidate: str) -> dict[str, object]:
    turns = parse_turns(row["DiscussionPlainText"])
    if len(turns) != 8:
        raise ValueError(f"Debate {row['DebateId']} has {len(turns)} turns")
    counts = Counter()
    for speaker, content in turns:
        counts[speaker] += word_count(content)
    opponent = "Model2" if candidate == "Model1" else "Model1"
    focal_words = counts[candidate]
    opponent_words = counts[opponent]
    gap = abs(focal_words - opponent_words) / max(focal_words, opponent_words)
    return {
        "candidate": candidate,
        "opponent": opponent,
        "focal_model": row[f"{candidate}name"],
        "opponent_model": row[f"{opponent}name"],
        "focal_position": row[f"{candidate}Position"],
        "focal_started": row["starting"] == candidate,
        "direction": "compression" if focal_words > opponent_words else "expansion",
        "focal_words": focal_words,
        "opponent_words": opponent_words,
        "gap": gap,
    }


def add_constraint(
    rows: list[dict[str, object]],
    lower: float,
    upper: float,
    matrix_rows: list[dict[int, float]],
    lowers: list[float],
    uppers: list[float],
) -> None:
    matrix_rows.append({int(row["variable"]): 1.0 for row in rows})
    lowers.append(lower)
    uppers.append(upper)


def main() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    source = read_csv(Path(config["source_csv"]))
    topics = topic_lookup(Path(config["topics_file"]))
    models = sorted({row["Model1name"] for row in source} | {row["Model2name"] for row in source})
    if len(source) != 240 or len(models) != 4:
        raise ValueError("Expected the validated 240-debate, four-model paper dataset")

    variables = []
    rows_by_id = {row["DebateId"]: row for row in source}
    for row in source:
        topic_id = topics.get((row["positionA"], row["positionB"]))
        if not topic_id:
            raise ValueError(f"Unknown topic for debate {row['DebateId']}")
        for candidate in ("Model1", "Model2"):
            meta = candidate_metadata(row, candidate)
            if float(meta["gap"]) < float(config["minimum_relative_length_gap"]):
                continue
            digest = hashlib.sha256(
                f"{config['sample_seed']}|{row['DebateId']}|{candidate}".encode()
            ).hexdigest()
            variables.append(
                {
                    **meta,
                    "variable": len(variables),
                    "debate_id": row["DebateId"],
                    "topic_id": topic_id,
                    "focal_slot": candidate,
                    "hash": digest,
                }
            )

    matrix_rows: list[dict[int, float]] = []
    lowers: list[float] = []
    uppers: list[float] = []
    for debate_id in sorted(rows_by_id, key=int):
        group = [row for row in variables if row["debate_id"] == debate_id]
        if group:
            add_constraint(group, 0, 1, matrix_rows, lowers, uppers)
    topic_ids = sorted(set(row["topic_id"] for row in variables))
    for topic_id in topic_ids:
        group = [row for row in variables if row["topic_id"] == topic_id]
        add_constraint(group, 10, 10, matrix_rows, lowers, uppers)
        compressed = [row for row in group if row["direction"] == "compression"]
        add_constraint(compressed, 5, 5, matrix_rows, lowers, uppers)
    for model in models:
        group = [row for row in variables if row["focal_model"] == model]
        add_constraint(group, 25, 25, matrix_rows, lowers, uppers)
    add_constraint(
        [row for row in variables if row["focal_slot"] == "Model1"],
        50,
        50,
        matrix_rows,
        lowers,
        uppers,
    )
    add_constraint(
        [row for row in variables if row["focal_position"] == "A"],
        50,
        50,
        matrix_rows,
        lowers,
        uppers,
    )
    add_constraint(
        [row for row in variables if row["focal_started"]],
        50,
        50,
        matrix_rows,
        lowers,
        uppers,
    )

    matrix = lil_matrix((len(matrix_rows), len(variables)), dtype=float)
    for row_index, values in enumerate(matrix_rows):
        for column, value in values.items():
            matrix[row_index, column] = value
    costs = np.array(
        [
            -float(row["gap"]) + int(str(row["hash"])[:8], 16) / (16**8) * 1e-6
            for row in variables
        ]
    )
    result = milp(
        c=costs,
        integrality=np.ones(len(variables)),
        bounds=Bounds(np.zeros(len(variables)), np.ones(len(variables))),
        constraints=LinearConstraint(matrix.tocsr(), np.array(lowers), np.array(uppers)),
        options={"time_limit": 60},
    )
    if not result.success:
        raise RuntimeError(f"Could not freeze a balanced sample: {result.message}")
    selected = [variables[index] for index, value in enumerate(result.x) if value > 0.5]
    if len(selected) != int(config["sample_size"]):
        raise ValueError(f"Expected {config['sample_size']} selected rows, found {len(selected)}")

    by_hash = sorted(selected, key=lambda row: row["hash"])
    focal_first = {row["debate_id"] for row in by_hash[: len(by_hash) // 2]}
    manifest_rows = []
    for item in sorted(selected, key=lambda row: int(str(row["debate_id"]))):
        row = rows_by_id[str(item["debate_id"])]
        manifest_rows.append(
            {
                "ProtocolVersion": config["protocol_version"],
                "DebateId": item["debate_id"],
                "TopicId": item["topic_id"],
                "FocalCandidate": item["candidate"],
                "OpponentCandidate": item["opponent"],
                "FocalModel": item["focal_model"],
                "OpponentModel": item["opponent_model"],
                "FocalPosition": item["focal_position"],
                "FocalStarted": str(bool(item["focal_started"])).lower(),
                "InterventionDirection": item["direction"],
                "FocalWordsOriginal": item["focal_words"],
                "OpponentWords": item["opponent_words"],
                "RelativeLengthGap": f"{float(item['gap']):.6f}",
                "TargetWords": item["opponent_words"],
                "PresentationOrder": (
                    "focal_first" if item["debate_id"] in focal_first else "focal_second"
                ),
                "SourceSha256": hashlib.sha256(
                    row["DiscussionPlainText"].encode("utf-8")
                ).hexdigest(),
            }
        )
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(manifest_rows)
    print(
        json.dumps(
            {
                "manifest": str(MANIFEST),
                "rows": len(manifest_rows),
                "topics": Counter(row["TopicId"] for row in manifest_rows),
                "focal_models": Counter(row["FocalModel"] for row in manifest_rows),
                "directions": Counter(row["InterventionDirection"] for row in manifest_rows),
                "focal_slots": Counter(row["FocalCandidate"] for row in manifest_rows),
                "focal_positions": Counter(row["FocalPosition"] for row in manifest_rows),
                "focal_started": Counter(row["FocalStarted"] for row in manifest_rows),
                "presentation": Counter(row["PresentationOrder"] for row in manifest_rows),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
