import json
from pathlib import Path


BASE = Path("topics/phase1_topics.json")
CONTROLS = Path("topics/extreme_control_topics.json")
OUTPUT = Path("topics/final_report_replication_topics.json")


def load(path: Path) -> list[dict[str, object]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list in {path}")
    return data


def main() -> None:
    base = load(BASE)
    controls = load(CONTROLS)
    if len(base) != 10:
        raise ValueError(f"Expected 10 original topics, found {len(base)}")
    if len(controls) != 4:
        raise ValueError(f"Expected four extreme controls, found {len(controls)}")

    easier = [str(item.get("expected_easier_position", "")) for item in controls]
    if sorted(easier) != ["A", "A", "B", "B"]:
        raise ValueError("Extreme controls must balance expected easier labels A and B")

    combined = base + controls
    ids = [str(item.get("id", "")) for item in combined]
    if len(ids) != len(set(ids)) or any(not value for value in ids):
        raise ValueError("Topic ids must be non-empty and unique")
    for item in combined:
        for field in ("question", "position_a", "position_b"):
            if not str(item.get(field, "")).strip():
                raise ValueError(f"Topic {item['id']} has no {field}")

    OUTPUT.write_text(
        json.dumps(combined, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {len(combined)} topics to {OUTPUT}: "
        f"{len(base)} original and {len(controls)} extreme controls."
    )


if __name__ == "__main__":
    main()
