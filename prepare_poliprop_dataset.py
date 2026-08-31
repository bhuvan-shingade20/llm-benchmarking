import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


DEFAULT_SOURCE = Path("data/external/poliprop/source")
DEFAULT_OUTPUT = Path("data/external/poliprop/PoliPropPrepared.jsonl")
DEFAULT_MANIFEST = Path("data/external/poliprop/manifest.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare the official PoliProp debates for forced-choice evaluation."
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--max-words-per-side", type=int, default=450)
    parser.add_argument("--sample-seed", default="20260829")
    parser.add_argument("--sample-per-winner", type=int, default=60)
    return parser.parse_args()


def normalize_text(value: object) -> str:
    return " ".join(str(value).split())


def balanced_side_excerpt(texts: list[str], max_words: int) -> str:
    if not texts:
        return ""
    normalized = [normalize_text(text) for text in texts]
    tokenized = [text.split() for text in normalized]
    allocations = [0] * len(tokenized)
    remaining = max_words
    active = {index for index, words in enumerate(tokenized) if words}
    while remaining and active:
        per_turn = max(1, remaining // len(active))
        for index in list(active):
            available = len(tokenized[index]) - allocations[index]
            take = min(per_turn, available, remaining)
            allocations[index] += take
            remaining -= take
            if allocations[index] == len(tokenized[index]):
                active.remove(index)
            if not remaining:
                break
    excerpts = []
    for index, (words, keep) in enumerate(zip(tokenized, allocations), start=1):
        if not keep:
            continue
        suffix = " [...]" if keep < len(words) else ""
        excerpts.append(f"Turn {index}: {' '.join(words[:keep])}{suffix}")
    return "\n\n".join(excerpts)


def released_ground_truth(tidy_root: Path, selected_ids: set[int]) -> dict[int, str]:
    q1 = pd.read_json(tidy_root / "llm_outputs" / "q1.json")
    q1 = q1[q1["debate_id"].isin(selected_ids)]
    conflicts = q1.groupby("debate_id")["ground_truth"].nunique()
    if (conflicts != 1).any():
        raise ValueError("The released q1 file has conflicting human labels.")
    return q1.groupby("debate_id")["ground_truth"].first().to_dict()


def deterministic_sample(
    records: list[dict[str, object]], seed: str, per_winner: int
) -> set[int]:
    chosen: set[int] = set()
    for winner in ("Pro", "Con"):
        candidates = [record for record in records if record["human_majority"] == winner]
        candidates.sort(
            key=lambda record: hashlib.sha256(
                f"{seed}:{record['debate_id']}".encode("utf-8")
            ).hexdigest()
        )
        if len(candidates) < per_winner:
            raise ValueError(f"Only {len(candidates)} {winner} cases are available.")
        chosen.update(int(record["debate_id"]) for record in candidates[:per_winner])
    return chosen


def main() -> None:
    args = parse_args()
    processing = args.source / "processing"
    tidy = args.source / "tidy" / "tidy"

    datasets = json.loads((tidy / "datasets" / "datasets.json").read_text(encoding="utf-8"))
    selected_ids = {int(value) for value in datasets["Trimmed"]}
    if len(selected_ids) != 833:
        raise ValueError(f"Expected 833 PoliProp debates, found {len(selected_ids)}")

    propositions = pd.read_json(processing / "propositions" / "propositions.json")
    propositions = propositions[propositions["debate_id"].isin(selected_ids)].set_index("debate_id")
    metadata = pd.read_json(processing / "filtered_data" / "debates_filtered_df.json")
    metadata = metadata[metadata["debate_id"].isin(selected_ids)].set_index("debate_id")
    rounds = pd.read_json(processing / "processed_data" / "rounds_df.json")
    rounds = rounds[rounds["debate_id"].isin(selected_ids)].sort_values(
        ["debate_id", "order"]
    )
    ground_truth = released_ground_truth(tidy, selected_ids)

    if set(propositions.index) != selected_ids:
        raise ValueError("Proposition coverage does not match the 833 selected debates.")
    if set(metadata.index) != selected_ids:
        raise ValueError("Metadata coverage does not match the 833 selected debates.")
    if set(rounds["debate_id"].unique()) != selected_ids:
        raise ValueError("Transcript coverage does not match the 833 selected debates.")
    if set(ground_truth) != selected_ids:
        raise ValueError("Human-label coverage does not match the 833 selected debates.")

    records: list[dict[str, object]] = []
    for debate_id, debate_rounds in rounds.groupby("debate_id", sort=True):
        pro_turns = debate_rounds.loc[debate_rounds["side"] == "Pro", "text"].tolist()
        con_turns = debate_rounds.loc[debate_rounds["side"] == "Con", "text"].tolist()
        if not pro_turns or not con_turns:
            raise ValueError(f"Debate {debate_id} does not contain both sides.")
        pro_excerpt = balanced_side_excerpt(pro_turns, args.max_words_per_side)
        con_excerpt = balanced_side_excerpt(con_turns, args.max_words_per_side)
        meta = metadata.loc[debate_id]
        records.append(
            {
                "debate_id": int(debate_id),
                "proposition": normalize_text(propositions.loc[debate_id, "proposition"]),
                "original_title": normalize_text(meta["title"]),
                "start_date": normalize_text(meta["start_date"]),
                "human_majority": ground_truth[int(debate_id)],
                "primary_eligible": ground_truth[int(debate_id)] in {"Pro", "Con"},
                "num_human_votes": int(meta["num_votes"]),
                "num_pro_turns": len(pro_turns),
                "num_con_turns": len(con_turns),
                "full_pro_words": sum(len(normalize_text(text).split()) for text in pro_turns),
                "full_con_words": sum(len(normalize_text(text).split()) for text in con_turns),
                "excerpt_pro_words": len(pro_excerpt.split()),
                "excerpt_con_words": len(con_excerpt.split()),
                "pro_excerpt": pro_excerpt,
                "con_excerpt": con_excerpt,
            }
        )

    counts = {label: sum(record["human_majority"] == label for record in records) for label in ("Pro", "Con", "Tie")}
    expected = {"Pro": 317, "Con": 423, "Tie": 93}
    if counts != expected:
        raise ValueError(f"Unexpected released-label counts: {counts}; expected {expected}")

    robustness_ids = deterministic_sample(records, args.sample_seed, args.sample_per_winner)
    for record in records:
        record["robustness_sample"] = int(record["debate_id"]) in robustness_ids

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    manifest = {
        "dataset": "PoliProp",
        "source_record": "https://zenodo.org/records/13887286",
        "source_code": "https://github.com/manoelhortaribeiro/debate-gpt-x",
        "license": "CC BY-NC-SA 3.0",
        "selected_debates": len(records),
        "human_majority_counts": counts,
        "primary_decisive_debates": counts["Pro"] + counts["Con"],
        "human_tie_debates": counts["Tie"],
        "max_words_per_side": args.max_words_per_side,
        "robustness_sample_seed": args.sample_seed,
        "robustness_sample_size": len(robustness_ids),
        "robustness_sample_counts": {"Pro": args.sample_per_winner, "Con": args.sample_per_winner},
    }
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
