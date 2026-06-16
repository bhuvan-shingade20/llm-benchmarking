import argparse
import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from run_conversation import (
    DEFAULT_JUDGE_MODEL,
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    DEFAULT_TOPICS_PATH,
    START_PROMPTS,
    DiscussionCase,
    Message,
    load_topics,
    run_conversation,
    save_transcript,
)


RESULTS_DIR = Path("results")


def parse_csv_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def extract_judge_result(transcript: list[Message]) -> dict[str, Any]:
    for message in reversed(transcript):
        if message.speaker == "Judge":
            try:
                return json.loads(message.content)
            except json.JSONDecodeError:
                return {"winner": "Judge parse error", "confidence": 0, "raw_output": message.content}
    return {"winner": "No judge", "confidence": 0}


def metric(result: dict[str, Any], agent_key: str, metric_name: str) -> Any:
    agent = result.get(agent_key, {})
    if isinstance(agent, dict):
        return agent.get(metric_name, "")
    return ""


def make_row(
    run_id: str,
    topic_id: str,
    question: str,
    position_a: str,
    position_b: str,
    provider: str,
    judge_model: str,
    role_assignment: str,
    start_style: str,
    position_a_model: str,
    position_b_model: str,
    transcript_json: Path,
    transcript_markdown: Path,
    judge_result: dict[str, Any],
) -> dict[str, Any]:
    winner = judge_result.get("winner", "")
    winning_model = ""
    if winner == "Agent A":
        winning_model = position_a_model
    elif winner == "Agent B":
        winning_model = position_b_model
    elif winner == "Tie":
        winning_model = "Tie"

    row: dict[str, Any] = {
        "run_id": run_id,
        "topic_id": topic_id,
        "question": question,
        "position_a": position_a,
        "position_b": position_b,
        "provider": provider,
        "role_assignment": role_assignment,
        "start_style": start_style,
        "position_a_model": position_a_model,
        "position_b_model": position_b_model,
        "judge_model": judge_model,
        "winner": winner,
        "winning_model": winning_model,
        "confidence": judge_result.get("confidence", ""),
        "transcript_json": str(transcript_json),
        "transcript_markdown": str(transcript_markdown),
    }

    metric_names = [
        "argument_quality",
        "evidence_specificity",
        "factfulness",
        "rebuttal_strength",
        "groundedness",
        "symmetry",
        "stance_consistency",
        "adaptability",
        "clarity",
        "overall_persuasiveness",
    ]
    for name in metric_names:
        row[f"position_a_{name}"] = metric(judge_result, "agent_a", name)
        row[f"position_b_{name}"] = metric(judge_result, "agent_b", name)

    for_unsupported = metric(judge_result, "agent_a", "unsupported_claims")
    against_unsupported = metric(judge_result, "agent_b", "unsupported_claims")
    row["position_a_unsupported_claims"] = json.dumps(for_unsupported, ensure_ascii=False)
    row["position_b_unsupported_claims"] = json.dumps(against_unsupported, ensure_ascii=False)
    row["decisive_reasons"] = json.dumps(judge_result.get("decisive_reasons", []), ensure_ascii=False)
    return row


def write_results(rows: list[dict[str, Any]], run_id: str) -> tuple[Path, Path]:
    RESULTS_DIR.mkdir(exist_ok=True)
    json_path = RESULTS_DIR / f"{run_id}_results.json"
    csv_path = RESULTS_DIR / f"{run_id}_results.csv"

    json_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    if rows:
        with csv_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    else:
        csv_path.write_text("", encoding="utf-8")

    return json_path, csv_path


def build_runs(
    cases: list[DiscussionCase],
    model_a: str,
    model_b: str,
    side_swap: bool,
    models: list[str],
    start_styles: list[str],
) -> list[dict[str, str]]:
    runs: list[dict[str, str]] = []
    if models:
        model_pairs = [(left, right) for left in models for right in models if left != right]
    else:
        model_pairs = [(model_a, model_b)]
        if side_swap and model_a != model_b:
            model_pairs.append((model_b, model_a))

    for case in cases:
        for start_style in start_styles:
            for pair_index, (position_a_model, position_b_model) in enumerate(model_pairs, start=1):
                role_assignment = "original" if (position_a_model, position_b_model) == (model_a, model_b) else "permuted"
                if not models and side_swap and (position_a_model, position_b_model) == (model_b, model_a):
                    role_assignment = "swapped"
                runs.append(
                    {
                        "topic_id": case.id or "",
                        "question": case.question,
                        "position_a": case.position_a,
                        "position_b": case.position_b,
                        "role_assignment": role_assignment,
                        "start_style": start_style,
                        "position_a_model": position_a_model,
                        "position_b_model": position_b_model,
                        "label": f"{case.id}_{start_style}_pair{pair_index:02d}",
                    }
                )
    return runs


def filter_cases_by_ids(cases: list[DiscussionCase], topic_ids: list[str]) -> list[DiscussionCase]:
    if not topic_ids:
        return cases

    requested = set(topic_ids)
    selected = [case for case in cases if case.id in requested]
    found = {case.id for case in selected}
    missing = [topic_id for topic_id in topic_ids if topic_id not in found]
    if missing:
        available = ", ".join(case.id or "" for case in cases)
        raise ValueError(f"Topic id(s) not found: {', '.join(missing)}. Available topic ids: {available}")
    return selected


def parse_args() -> argparse.Namespace:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run a batch LLM discussion benchmark with model-role assignments.")
    parser.add_argument("--topics", default=str(DEFAULT_TOPICS_PATH), help="JSON or text file containing topics.")
    parser.add_argument(
        "--topic-id",
        "--topic-ids",
        dest="topic_ids",
        default="",
        help="Topic id or comma-separated topic ids to run from the topics file.",
    )
    parser.add_argument("--provider", default=os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER), choices=["ollama", "openai"])
    parser.add_argument("--model-a", default=os.getenv("MODEL_A", DEFAULT_MODEL), help="First model to benchmark.")
    parser.add_argument("--model-b", default=os.getenv("MODEL_B", DEFAULT_MODEL), help="Second model to benchmark.")
    parser.add_argument(
        "--models",
        default=os.getenv("MODEL_POOL", ""),
        help="Comma-separated model IDs. If set, runs all ordered model-role permutations.",
    )
    parser.add_argument(
        "--judge-model",
        default=os.getenv("MODEL_JUDGE", os.getenv("MODEL_A", DEFAULT_JUDGE_MODEL)),
        help="Model used to judge each debate.",
    )
    parser.add_argument("--turns", type=int, default=4, help="Debate turns before closing statements.")
    parser.add_argument("--max-tokens", type=int, default=220, help="Maximum tokens per debate turn.")
    parser.add_argument("--limit", type=int, help="Limit number of topics for quick tests.")
    parser.add_argument(
        "--start-styles",
        default="neutral",
        help=f"Comma-separated moderator start styles. Available: {', '.join(sorted(START_PROMPTS))}.",
    )
    parser.add_argument("--no-side-swap", action="store_true", help="Disable the reversed default model-role run.")
    parser.add_argument("--no-judge", action="store_true", help="Disable judging.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned runs without calling models.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cases = load_topics(Path(args.topics))
    cases = filter_cases_by_ids(cases, parse_csv_list(args.topic_ids))
    if args.limit is not None:
        cases = cases[: args.limit]
    if not cases:
        raise SystemExit("No topics found.")
    models = parse_csv_list(args.models)
    start_styles = parse_csv_list(args.start_styles) or ["neutral"]
    invalid_start_styles = [style for style in start_styles if style not in START_PROMPTS]
    if invalid_start_styles:
        raise SystemExit(f"Invalid start style(s): {', '.join(invalid_start_styles)}")

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_benchmark")
    planned_runs = build_runs(
        cases=cases,
        model_a=args.model_a,
        model_b=args.model_b,
        side_swap=not args.no_side_swap,
        models=models,
        start_styles=start_styles,
    )

    print(f"Benchmark run id: {run_id}")
    print(f"Provider: {args.provider}")
    print(f"Model A: {args.model_a}")
    print(f"Model B: {args.model_b}")
    if models:
        print(f"Model pool: {', '.join(models)}")
    print(f"Judge: {'disabled' if args.no_judge else args.judge_model}")
    print(f"Start styles: {', '.join(start_styles)}")
    print(f"Topics: {len(cases)} | Planned debates: {len(planned_runs)}")

    if args.dry_run:
        for index, run in enumerate(planned_runs, start=1):
            print(
                f"{index}. {run['label']} | Position A={run['position_a_model']} | "
                f"Position B={run['position_b_model']} | start={run['start_style']} | {run['question']}"
            )
        return

    rows: list[dict[str, Any]] = []
    for index, run in enumerate(planned_runs, start=1):
        print(f"\n=== Debate {index}/{len(planned_runs)}: {run['label']} ===")
        print(f"Question: {run['question']}")
        print(f"Start style: {run['start_style']}")
        print(f"Position A model: {run['position_a_model']}")
        print(f"Position B model: {run['position_b_model']}")

        transcript = run_conversation(
            topic=run["question"],
            turns=args.turns,
            provider=args.provider,
            model_a=run["position_a_model"],
            model_b=run["position_b_model"],
            judge_model=args.judge_model,
            judge_enabled=not args.no_judge,
            max_tokens=args.max_tokens,
            position_a=run["position_a"],
            position_b=run["position_b"],
            start_style=run["start_style"],
        )
        transcript_json, transcript_markdown = save_transcript(
            transcript,
            run["question"],
            run_label=f"{run_id}_{run['label']}",
        )
        judge_result = extract_judge_result(transcript)
        rows.append(
            make_row(
                run_id=run_id,
                topic_id=run["topic_id"],
                question=run["question"],
                position_a=run["position_a"],
                position_b=run["position_b"],
                provider=args.provider,
                judge_model="" if args.no_judge else args.judge_model,
                role_assignment=run["role_assignment"],
                start_style=run["start_style"],
                position_a_model=run["position_a_model"],
                position_b_model=run["position_b_model"],
                transcript_json=transcript_json,
                transcript_markdown=transcript_markdown,
                judge_result=judge_result,
            )
        )

        results_json, results_csv = write_results(rows, run_id)
        print(f"Partial results saved: {results_csv}")

    results_json, results_csv = write_results(rows, run_id)
    print("\nBenchmark completed")
    print(f"Results JSON: {results_json}")
    print(f"Results CSV: {results_csv}")


if __name__ == "__main__":
    main()
