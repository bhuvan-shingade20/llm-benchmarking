import argparse
import csv
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from run_conversation import build_client, complete_chat


DEFAULT_JUDGES = [
    "gemma-4-31b-it",
    "qwen3-30b-a3b-instruct-2507",
    "glm-4.7",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate DiffPosJudgements.csv and SamePosJudgements.csv.")
    parser.add_argument("--raw", required=True, help="RawDebates.csv path. Model1/2 format or ModelA/B source format.")
    parser.add_argument("--out-dir", required=True, help="Output directory for judgement CSVs.")
    parser.add_argument(
        "--mode",
        choices=("diff", "same", "both"),
        default="both",
        help="Generate different-position judgments, same-position judgments, or both.",
    )
    parser.add_argument("--wait-for-rows", type=int, default=0, help="Wait until raw CSV has at least this many rows.")
    parser.add_argument("--judges", default=",".join(DEFAULT_JUDGES), help="Comma-separated judge model names.")
    parser.add_argument("--max-new-calls", type=int, help="Stop after this many new judge calls.")
    parser.add_argument("--sleep", type=int, default=120, help="Seconds to sleep while waiting for raw rows.")
    parser.add_argument("--call-delay", type=int, default=20, help="Seconds to wait after each successful judge call.")
    parser.add_argument("--rate-limit-sleep", type=int, default=600, help="Seconds to wait after a rate-limit failure.")
    return parser.parse_args()


def model1_fields() -> list[str]:
    return [
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


def modelab_fields() -> list[str]:
    return [
        "DebateId",
        "ModelAname",
        "ModelBname",
        "positionA",
        "positionB",
        "DiscussionPlainText",
        "starting",
    ]


def relabel_discussion(text: str, old_a_is_model1: bool) -> str:
    placeholder_a = "__MODEL_A_LABEL__"
    placeholder_b = "__MODEL_B_LABEL__"
    text = text.replace("ModelA:", f"{placeholder_a}:")
    text = text.replace("ModelB:", f"{placeholder_b}:")
    if old_a_is_model1:
        return text.replace(placeholder_a, "Model1").replace(placeholder_b, "Model2")
    return text.replace(placeholder_a, "Model2").replace(placeholder_b, "Model1")


def normalize_modelab_row(row: dict[str, str]) -> dict[str, str]:
    old_a = row["ModelAname"]
    old_b = row["ModelBname"]
    model1, model2 = sorted([old_a, old_b])
    old_a_is_model1 = old_a == model1
    old_starting_model = old_a if row["starting"] == "A" else old_b
    return {
        "DebateId": row["DebateId"],
        "Model1name": model1,
        "Model2name": model2,
        "positionA": row["positionA"],
        "positionB": row["positionB"],
        "Model1Position": "A" if old_a_is_model1 else "B",
        "Model2Position": "B" if old_a_is_model1 else "A",
        "DiscussionPlainText": relabel_discussion(row["DiscussionPlainText"], old_a_is_model1),
        "starting": "Model1" if old_starting_model == model1 else "Model2",
    }


def read_raw_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        if reader.fieldnames == model1_fields():
            return rows
        if reader.fieldnames == modelab_fields():
            return [normalize_modelab_row(row) for row in rows]
        raise ValueError(f"Unexpected raw debate columns: {reader.fieldnames}")


def wait_for_raw(path: Path, target_rows: int, sleep_seconds: int) -> list[dict[str, str]]:
    while True:
        rows = read_raw_rows(path)
        if len(rows) >= target_rows:
            return rows
        print(f"Waiting for raw debates: {len(rows)}/{target_rows} rows ready.")
        time.sleep(sleep_seconds)


def diff_fields(judges: list[str]) -> list[str]:
    fields = ["DebateId"]
    for index, judge in enumerate(judges, start=1):
        label = f"Judge {index} ({judge})"
        fields.extend([f"{label} winner", f"{label} winningPosition", f"{label} confidence"])
    return fields


def same_fields(judges: list[str]) -> list[str]:
    fields = [
        "DebateId1",
        "DebateId2",
        "positionA",
        "positionB",
        "testedPosition",
        "candidate1Model",
        "candidate2Model",
        "candidateStarting",
    ]
    for index, judge in enumerate(judges, start=1):
        label = f"Judge {index} ({judge})"
        fields.extend([f"{label} winner", f"{label} confidence"])
    return fields


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def parse_json_result(text: str) -> dict[str, object]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`").strip()
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1:
        stripped = stripped[start : end + 1]
    return json.loads(stripped)


def is_rate_limit_error(error: Exception) -> bool:
    text = str(error).lower()
    return "rate limit" in text or "429" in text


def call_judge(judge: str, system_prompt: str, user_prompt: str, rate_limit_sleep: int) -> dict[str, object]:
    client = build_client("openai")
    last_error: Exception | None = None
    for attempt in range(1, 8):
        try:
            content = complete_chat(
                client=client,
                model=judge,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=220,
                temperature=0.1,
            )
            return parse_json_result(content)
        except Exception as error:
            last_error = error
            if attempt < 7:
                wait_seconds = rate_limit_sleep if is_rate_limit_error(error) else 60 * attempt
                print(
                    f"Judge {judge} failed on attempt {attempt}: {error}. Retrying in {wait_seconds} seconds.",
                    flush=True,
                )
                time.sleep(wait_seconds)
    raise RuntimeError(f"Judge {judge} failed after retries: {last_error}") from last_error


def normalize_winner(value: object, allowed: list[str]) -> str:
    text = str(value or "").strip()
    if text in allowed:
        return text
    lowered = text.lower()
    for option in allowed:
        if option.lower() == lowered:
            return option
    if "tie" in lowered:
        return "Tie"
    for option in allowed:
        if option.lower() in lowered:
            return option
    return "Tie"


def confidence_value(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    return f"{max(0.0, min(1.0, number)):.2f}"


def diff_prompt(row: dict[str, str]) -> tuple[str, str]:
    system_prompt = """
You are an impartial debate judge.
Select which model argued its assigned position better in this debate.
Judge argument quality, responsiveness, factual discipline, and persuasive clarity.
Do not judge which policy position you personally agree with.
Return only valid JSON.
""".strip()
    user_prompt = f"""
positionA:
{row['positionA']}

positionB:
{row['positionB']}

Model1 argued position {row['Model1Position']}.
Model2 argued position {row['Model2Position']}.
Starting model: {row['starting']}.

Discussion:
{row['DiscussionPlainText']}

Return JSON exactly in this shape:
{{
  "winner": "{row['Model1name']}",
  "confidence": 0.0
}}

The winner must be exactly one of:
- {row['Model1name']}
- {row['Model2name']}
- Tie
""".strip()
    return system_prompt, user_prompt


def make_diff_rows(
    raw_rows: list[dict[str, str]],
    judges: list[str],
    output: Path,
    max_new_calls: int | None,
    call_delay: int,
    rate_limit_sleep: int,
) -> int:
    fields = diff_fields(judges)
    rows_by_id = {row.get("DebateId", ""): row for row in read_rows(output)}
    output_rows: list[dict[str, str]] = []
    new_calls = 0
    for raw in raw_rows:
        row = rows_by_id.get(raw["DebateId"], {"DebateId": raw["DebateId"]})
        for index, judge in enumerate(judges, start=1):
            label = f"Judge {index} ({judge})"
            winner_col = f"{label} winner"
            if row.get(winner_col):
                continue
            system_prompt, user_prompt = diff_prompt(raw)
            result = call_judge(judge, system_prompt, user_prompt, rate_limit_sleep)
            winner = normalize_winner(result.get("winner"), [raw["Model1name"], raw["Model2name"], "Tie"])
            row[winner_col] = winner
            if winner == raw["Model1name"]:
                row[f"{label} winningPosition"] = raw["Model1Position"]
            elif winner == raw["Model2name"]:
                row[f"{label} winningPosition"] = raw["Model2Position"]
            else:
                row[f"{label} winningPosition"] = "Tie"
            row[f"{label} confidence"] = confidence_value(result.get("confidence"))
            rows_by_id[raw["DebateId"]] = row
            new_calls += 1
            write_rows(output, fields, [rows_by_id[key] for key in sorted(rows_by_id, key=lambda value: int(value))])
            time.sleep(call_delay)
            if max_new_calls and new_calls >= max_new_calls:
                return new_calls
        output_rows.append(row)
    write_rows(output, fields, [rows_by_id[key] for key in sorted(rows_by_id, key=lambda value: int(value))])
    return new_calls


def model_for_position(row: dict[str, str], position: str) -> str:
    if row["Model1Position"] == position:
        return row["Model1name"]
    return row["Model2name"]


def candidate_starts(row: dict[str, str], position: str) -> bool:
    return (row["starting"] == "Model1" and row["Model1Position"] == position) or (
        row["starting"] == "Model2" and row["Model2Position"] == position
    )


def build_samepos_comparisons(raw_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    groups: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in raw_rows:
        groups[(row["positionA"], row["positionB"], row["Model1name"], row["Model2name"])].append(row)

    comparisons: list[dict[str, str]] = []
    for (_position_a, _position_b, _model1, _model2), rows in sorted(groups.items()):
        for tested in ("A", "B"):
            for starts in (True, False):
                candidates = [row for row in rows if candidate_starts(row, tested) == starts]
                by_model = {model_for_position(row, tested): row for row in candidates}
                if len(by_model) != 2:
                    continue
                model_names = sorted(by_model)
                for candidate1, candidate2 in (
                    (model_names[0], model_names[1]),
                    (model_names[1], model_names[0]),
                ):
                    row1 = by_model[candidate1]
                    row2 = by_model[candidate2]
                    comparisons.append(
                        {
                            "DebateId1": row1["DebateId"],
                            "DebateId2": row2["DebateId"],
                            "positionA": row1["positionA"],
                            "positionB": row1["positionB"],
                            "testedPosition": tested,
                            "candidate1Model": candidate1,
                            "candidate2Model": candidate2,
                            "candidateStarting": "yes" if starts else "no",
                        }
                    )
    return sorted(comparisons, key=lambda row: (int(row["DebateId1"]), int(row["DebateId2"]), row["testedPosition"]))


def same_prompt(comparison: dict[str, str], raw_by_id: dict[str, dict[str, str]]) -> tuple[str, str]:
    row1 = raw_by_id[comparison["DebateId1"]]
    row2 = raw_by_id[comparison["DebateId2"]]
    tested = comparison["testedPosition"]
    position_text = row1["positionA"] if tested == "A" else row1["positionB"]
    system_prompt = """
You are an impartial debate judge.
Compare two candidates that argued for the same assigned position in two separate debates.
Judge only which candidate argued the tested position better.
Do not reward the opposing side in either debate.
Return only valid JSON.
""".strip()
    user_prompt = f"""
positionA:
{row1['positionA']}

positionB:
{row1['positionB']}

Tested position: {tested}
Tested position text:
{position_text}

Candidate 1 model: {comparison['candidate1Model']}
Candidate 1 debate id: {comparison['DebateId1']}
Candidate 1 discussion:
{row1['DiscussionPlainText']}

Candidate 2 model: {comparison['candidate2Model']}
Candidate 2 debate id: {comparison['DebateId2']}
Candidate 2 discussion:
{row2['DiscussionPlainText']}

Return JSON exactly in this shape:
{{
  "winner": "{comparison['candidate1Model']}",
  "confidence": 0.0
}}

The winner must be exactly one of:
- {comparison['candidate1Model']}
- {comparison['candidate2Model']}
- Tie
""".strip()
    return system_prompt, user_prompt


def make_same_rows(
    raw_rows: list[dict[str, str]],
    judges: list[str],
    output: Path,
    max_new_calls: int | None,
    call_delay: int,
    rate_limit_sleep: int,
) -> int:
    fields = same_fields(judges)
    raw_by_id = {row["DebateId"]: row for row in raw_rows}
    existing_key = lambda row: (row.get("DebateId1", ""), row.get("DebateId2", ""), row.get("testedPosition", ""), row.get("candidateStarting", ""))
    rows_by_key = {existing_key(row): row for row in read_rows(output)}
    comparisons = build_samepos_comparisons(raw_rows)
    new_calls = 0
    for comparison in comparisons:
        key = existing_key(comparison)
        row = rows_by_key.get(key, dict(comparison))
        for index, judge in enumerate(judges, start=1):
            label = f"Judge {index} ({judge})"
            winner_col = f"{label} winner"
            confidence_col = f"{label} confidence"
            if row.get(winner_col) and row.get(confidence_col):
                continue
            system_prompt, user_prompt = same_prompt(comparison, raw_by_id)
            result = call_judge(judge, system_prompt, user_prompt, rate_limit_sleep)
            row[winner_col] = normalize_winner(
                result.get("winner"),
                [comparison["candidate1Model"], comparison["candidate2Model"], "Tie"],
            )
            row[confidence_col] = confidence_value(result.get("confidence"))
            rows_by_key[key] = row
            new_calls += 1
            ordered = sorted(rows_by_key.values(), key=lambda value: (int(value["DebateId1"]), int(value["DebateId2"]), value["testedPosition"]))
            write_rows(output, fields, ordered)
            time.sleep(call_delay)
            if max_new_calls and new_calls >= max_new_calls:
                return new_calls
    ordered = sorted(rows_by_key.values(), key=lambda value: (int(value["DebateId1"]), int(value["DebateId2"]), value["testedPosition"]))
    write_rows(output, fields, ordered)
    return new_calls


def main() -> None:
    args = parse_args()
    raw_path = Path(args.raw)
    out_dir = Path(args.out_dir)
    judges = [judge.strip() for judge in args.judges.split(",") if judge.strip()]
    raw_rows = wait_for_raw(raw_path, args.wait_for_rows, args.sleep) if args.wait_for_rows else read_raw_rows(raw_path)
    raw_rows = sorted(raw_rows, key=lambda row: int(row["DebateId"]))
    out_dir.mkdir(parents=True, exist_ok=True)
    diff_output = out_dir / "DiffPosJudgements.csv"
    same_output = out_dir / "SamePosJudgements.csv"

    new_calls = 0
    if args.mode in {"diff", "both"}:
        new_calls = make_diff_rows(
            raw_rows,
            judges,
            diff_output,
            args.max_new_calls,
            args.call_delay,
            args.rate_limit_sleep,
        )
        if args.max_new_calls and new_calls >= args.max_new_calls:
            print(f"Added {new_calls} judge calls; stopping after DiffPos progress.")
            return
    remaining = None if args.max_new_calls is None else args.max_new_calls - new_calls
    same_calls = 0
    if args.mode in {"same", "both"}:
        same_calls = make_same_rows(
            raw_rows,
            judges,
            same_output,
            remaining,
            args.call_delay,
            args.rate_limit_sleep,
        )
    print(f"Added {new_calls + same_calls} judge calls.")


if __name__ == "__main__":
    main()
