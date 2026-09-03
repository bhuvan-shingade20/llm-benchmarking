import argparse
import csv
import zipfile
from pathlib import Path


INPUT_FIELDS = [
    "DebateId",
    "ModelAname",
    "ModelBname",
    "positionA",
    "positionB",
    "DiscussionPlainText",
    "starting",
]

OUTPUT_FIELDS = [
    "DebateId",
    "Model1name",
    "Model2name",
    "positionA",
    "positionB",
    "Model1Position",
    "Model2Position",
    "DiscussionPlainText",
    "starting",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert raw debates from ModelA/B labels to Model1/2 labels.")
    parser.add_argument(
        "--input",
        default="runs/raw/RawDebates_modelAB_source.csv",
        help="Input RawDebates.csv that uses ModelA/ModelB participant labels.",
    )
    parser.add_argument(
        "--output",
        default="runs/raw/RawDebates.csv",
        help="Output RawDebates.csv that uses Model1/Model2 participant labels.",
    )
    return parser.parse_args()


def relabel_discussion(text: str, old_a_is_model1: bool) -> str:
    placeholder_a = "__MODEL_A_LABEL__"
    placeholder_b = "__MODEL_B_LABEL__"
    text = text.replace("ModelA:", f"{placeholder_a}:")
    text = text.replace("ModelB:", f"{placeholder_b}:")
    if old_a_is_model1:
        return text.replace(placeholder_a, "Model1").replace(placeholder_b, "Model2")
    return text.replace(placeholder_a, "Model2").replace(placeholder_b, "Model1")


def convert_row(row: dict[str, str], debate_id: int) -> dict[str, str]:
    old_a = row["ModelAname"]
    old_b = row["ModelBname"]
    model1, model2 = sorted([old_a, old_b])
    old_a_is_model1 = old_a == model1
    model1_position = "A" if old_a_is_model1 else "B"
    model2_position = "B" if old_a_is_model1 else "A"

    old_starting_model = old_a if row["starting"] == "A" else old_b
    starting = "Model1" if old_starting_model == model1 else "Model2"

    return {
        "DebateId": str(debate_id),
        "Model1name": model1,
        "Model2name": model2,
        "positionA": row["positionA"],
        "positionB": row["positionB"],
        "Model1Position": model1_position,
        "Model2Position": model2_position,
        "DiscussionPlainText": relabel_discussion(row["DiscussionPlainText"], old_a_is_model1),
        "starting": starting,
    }


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    with input_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != INPUT_FIELDS:
            raise ValueError(f"{input_path} has columns {reader.fieldnames}; expected {INPUT_FIELDS}.")
        source_rows = list(reader)
        if len(source_rows) != len({row["DebateId"] for row in source_rows}):
            raise ValueError("Input contains duplicate DebateId values.")
        rows = [convert_row(row, int(row["DebateId"])) for row in source_rows]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    zip_path = output_path.parent.with_suffix(".zip")
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(output_path, arcname="RawDebates.csv")

    print(f"Wrote {len(rows)} rows to {output_path}")
    print(f"Wrote zip to {zip_path}")


if __name__ == "__main__":
    main()
