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
    JUDGE_MODES,
    START_PROMPTS,
    DiscussionCase,
    Message,
    ModelSpec,
    build_client,
    judge_conversation,
    load_topics,
    make_discussion_case,
    model_label,
    parse_model_spec,
    print_message,
    run_conversation,
    save_transcript,
)


RESULTS_DIR = Path("results")
BENCHMARK_MODES = {"single", "paired", "permutations"}


def parse_csv_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_model_list(value: str | None, default_provider: str) -> list[ModelSpec]:
    return [parse_model_spec(item, default_provider) for item in parse_csv_list(value)]


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
    debate_id: str,
    benchmark_mode: str,
    pair_id: str,
    round_index: int,
    topic_id: str,
    question: str,
    position_a: str,
    position_b: str,
    provider: str,
    judge_model: str,
    judge_provider: str,
    judge_mode: str,
    role_assignment: str,
    start_style: str,
    position_a_model: str,
    position_a_provider: str,
    position_b_model: str,
    position_b_provider: str,
    transcript_json: Path,
    transcript_markdown: Path,
    judge_result: dict[str, Any],
) -> dict[str, Any]:
    winner = judge_result.get("winner", "")
    winning_model = ""
    winning_provider = ""
    if winner == "Agent A":
        winning_model = position_a_model
        winning_provider = position_a_provider
    elif winner == "Agent B":
        winning_model = position_b_model
        winning_provider = position_b_provider
    elif winner == "Tie":
        winning_model = "Tie"
        winning_provider = "Tie"

    row: dict[str, Any] = {
        "run_id": run_id,
        "debate_id": debate_id,
        "benchmark_mode": benchmark_mode,
        "pair_id": pair_id,
        "round_index": round_index,
        "topic_id": topic_id,
        "question": question,
        "position_a": position_a,
        "position_b": position_b,
        "provider": provider,
        "role_assignment": role_assignment,
        "start_style": start_style,
        "position_a_provider": position_a_provider,
        "position_a_model": position_a_model,
        "position_b_provider": position_b_provider,
        "position_b_model": position_b_model,
        "judge_provider": judge_provider,
        "judge_model": judge_model,
        "judge_mode": judge_mode,
        "winner": winner,
        "winning_provider": winning_provider,
        "winning_model": winning_model,
        "winning_model_label": f"{winning_provider}:{winning_model}" if winning_provider not in {"", "Tie"} else winning_model,
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
    row["judge_reason"] = judge_result.get("reason", "")
    row["run_error"] = judge_result.get("run_error", "")
    row["judge_result_json"] = json.dumps(judge_result, ensure_ascii=False)
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
    model_a: ModelSpec,
    model_b: ModelSpec,
    models: list[ModelSpec],
    start_styles: list[str],
    benchmark_mode: str,
) -> list[dict[str, str]]:
    runs: list[dict[str, str]] = []

    model_pairs: list[dict[str, Any]] = []
    if benchmark_mode == "single":
        model_pairs.append(
            {
                "position_a_provider": model_a.provider,
                "position_a_model": model_a.model,
                "position_b_provider": model_b.provider,
                "position_b_model": model_b.model,
                "role_assignment": "single",
                "pair_id": "pair01",
                "round_index": 1,
            }
        )
    elif benchmark_mode == "paired":
        base_pairs = []
        if models:
            for left_index, left in enumerate(models):
                for right in models[left_index + 1 :]:
                    base_pairs.append((left, right))
        else:
            base_pairs.append((model_a, model_b))

        for pair_index, (left, right) in enumerate(base_pairs, start=1):
            pair_id = f"pair{pair_index:02d}"
            model_pairs.append(
                {
                    "position_a_provider": left.provider,
                    "position_a_model": left.model,
                    "position_b_provider": right.provider,
                    "position_b_model": right.model,
                    "role_assignment": "paired_round_1",
                    "pair_id": pair_id,
                    "round_index": 1,
                }
            )
            if left != right:
                model_pairs.append(
                    {
                        "position_a_provider": right.provider,
                        "position_a_model": right.model,
                        "position_b_provider": left.provider,
                        "position_b_model": left.model,
                        "role_assignment": "paired_round_2",
                        "pair_id": pair_id,
                        "round_index": 2,
                    }
                )
    elif benchmark_mode == "permutations":
        pool = models or [model_a, model_b]
        for pair_index, (left, right) in enumerate(
            [(left, right) for left in pool for right in pool if left != right],
            start=1,
        ):
            model_pairs.append(
                {
                    "position_a_provider": left.provider,
                    "position_a_model": left.model,
                    "position_b_provider": right.provider,
                    "position_b_model": right.model,
                    "role_assignment": "permuted",
                    "pair_id": f"pair{pair_index:02d}",
                    "round_index": 1,
                }
            )
    else:
        raise ValueError(f"Unsupported benchmark mode: {benchmark_mode}")

    for case in cases:
        for start_style in start_styles:
            for pair in model_pairs:
                label = f"{case.id}_{benchmark_mode}_{start_style}_{pair['pair_id']}_r{pair['round_index']}"
                runs.append(
                    {
                        "topic_id": case.id or "",
                        "question": case.question,
                        "position_a": case.position_a,
                        "position_b": case.position_b,
                        "benchmark_mode": benchmark_mode,
                        "role_assignment": pair["role_assignment"],
                        "start_style": start_style,
                        "position_a_provider": pair["position_a_provider"],
                        "position_a_model": pair["position_a_model"],
                        "position_b_provider": pair["position_b_provider"],
                        "position_b_model": pair["position_b_model"],
                        "pair_id": pair["pair_id"],
                        "round_index": str(pair["round_index"]),
                        "label": label,
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
    parser.add_argument("--provider-a", choices=["ollama", "openai"], help="Provider for Position A model. Defaults to --provider or a provider prefix in --model-a.")
    parser.add_argument("--provider-b", choices=["ollama", "openai"], help="Provider for Position B model. Defaults to --provider or a provider prefix in --model-b.")
    parser.add_argument("--model-a", default=os.getenv("MODEL_A", DEFAULT_MODEL), help="First model to benchmark.")
    parser.add_argument("--model-b", default=os.getenv("MODEL_B", DEFAULT_MODEL), help="Second model to benchmark.")
    parser.add_argument(
        "--models",
        default=os.getenv("MODEL_POOL", ""),
        help="Comma-separated model IDs. Prefix with provider for mixed runs, e.g. ollama:llama3.2:3b,openai:gemma-4-31b-it.",
    )
    parser.add_argument("--judge-provider", choices=["ollama", "openai"], help="Provider for --judge-model when no provider prefix is used.")
    parser.add_argument(
        "--judge-model",
        default=os.getenv("MODEL_JUDGE", os.getenv("MODEL_A", DEFAULT_JUDGE_MODEL)),
        help="Model used to judge each debate.",
    )
    parser.add_argument(
        "--judge-models",
        default=os.getenv("JUDGE_MODEL_POOL", ""),
        help="Comma-separated judge model IDs. Prefix with provider for mixed local/cloud judges.",
    )
    parser.add_argument(
        "--judge-mode",
        default="detailed",
        choices=["both", *sorted(JUDGE_MODES)],
        help="Use winner_only, detailed, or both to compare quick decisions with detailed fact-checking evaluation.",
    )
    parser.add_argument(
        "--benchmark-mode",
        "--mode",
        dest="benchmark_mode",
        choices=sorted(BENCHMARK_MODES),
        help="single runs one model-role assignment; paired runs both reversed rounds; permutations runs all ordered model-role pairs.",
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
    model_a = parse_model_spec(args.model_a, args.provider_a or args.provider)
    model_b = parse_model_spec(args.model_b, args.provider_b or args.provider)
    models = parse_model_list(args.models, args.provider)
    judge_models = parse_model_list(args.judge_models, args.judge_provider or args.provider)
    if not judge_models:
        judge_models = [parse_model_spec(args.judge_model, args.judge_provider or args.provider)]
    benchmark_mode = args.benchmark_mode or ("permutations" if models else "paired")
    if args.no_side_swap:
        benchmark_mode = "single"
    start_styles = parse_csv_list(args.start_styles) or ["neutral"]
    invalid_start_styles = [style for style in start_styles if style not in START_PROMPTS]
    if invalid_start_styles:
        raise SystemExit(f"Invalid start style(s): {', '.join(invalid_start_styles)}")

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_benchmark")
    planned_runs = build_runs(
        cases=cases,
        model_a=model_a,
        model_b=model_b,
        models=models,
        start_styles=start_styles,
        benchmark_mode=benchmark_mode,
    )

    judge_modes = [] if args.no_judge else (["winner_only", "detailed"] if args.judge_mode == "both" else [args.judge_mode])

    print(f"Benchmark run id: {run_id}")
    print(f"Default provider: {args.provider}")
    print(f"Model A: {model_label(model_a)}")
    print(f"Model B: {model_label(model_b)}")
    if models:
        print(f"Model pool: {', '.join(model_label(model) for model in models)}")
    print(f"Benchmark mode: {benchmark_mode}")
    print(f"Judge: {'disabled' if args.no_judge else ', '.join(model_label(judge) for judge in judge_models)}")
    if judge_modes:
        print(f"Judge mode(s): {', '.join(judge_modes)}")
    print(f"Start styles: {', '.join(start_styles)}")
    print(f"Topics: {len(cases)} | Planned debates: {len(planned_runs)}")
    if judge_modes:
        print(f"Planned judge evaluations: {len(planned_runs) * len(judge_modes) * len(judge_models)}")

    if args.dry_run:
        for index, run in enumerate(planned_runs, start=1):
            print(
                f"{index}. {run['label']} | Position A={run['position_a_provider']}:{run['position_a_model']} | "
                f"Position B={run['position_b_provider']}:{run['position_b_model']} | mode={run['benchmark_mode']} | "
                f"round={run['round_index']} | start={run['start_style']} | {run['question']}"
            )
        return

    rows: list[dict[str, Any]] = []
    client_cache: dict[str, Any] = {}

    def get_client(provider: str) -> Any:
        if provider not in client_cache:
            client_cache[provider] = build_client(provider)
        return client_cache[provider]

    for index, run in enumerate(planned_runs, start=1):
        print(f"\n=== Debate {index}/{len(planned_runs)}: {run['label']} ===")
        print(f"Question: {run['question']}")
        print(f"Benchmark mode: {run['benchmark_mode']} | Pair: {run['pair_id']} | Round: {run['round_index']}")
        print(f"Start style: {run['start_style']}")
        print(f"Position A model: {run['position_a_provider']}:{run['position_a_model']}")
        print(f"Position B model: {run['position_b_provider']}:{run['position_b_model']}")

        evaluations: list[tuple[ModelSpec, str, dict[str, Any]]] = []
        try:
            transcript = run_conversation(
                topic=run["question"],
                turns=args.turns,
                provider=args.provider,
                model_a=run["position_a_model"],
                model_b=run["position_b_model"],
                judge_model=judge_models[0].model,
                judge_enabled=False,
                max_tokens=args.max_tokens,
                position_a=run["position_a"],
                position_b=run["position_b"],
                start_style=run["start_style"],
                provider_a=run["position_a_provider"],
                provider_b=run["position_b_provider"],
                judge_provider=judge_models[0].provider,
            )
        except Exception as error:
            error_text = f"Conversation failed: {error}"
            print(error_text)
            transcript = [
                Message(speaker="System", role="Start", content=f"Discussion question: {run['question']}"),
                Message(speaker="System", role="Run Error", content=error_text),
            ]
            evaluations.append(
                (
                    ModelSpec(provider="", model=""),
                    "",
                    {"winner": "Run error", "confidence": 0, "run_error": error_text},
                )
            )
        else:
            if args.no_judge:
                evaluations.append((ModelSpec(provider="", model=""), "", {"winner": "No judge", "confidence": 0}))
            else:
                case = make_discussion_case(
                    run["question"],
                    position_a=run["position_a"],
                    position_b=run["position_b"],
                    case_id=run["topic_id"],
                )
                for judge in judge_models:
                    for judge_mode in judge_modes:
                        try:
                            evaluation = judge_conversation(
                                client=get_client(judge.provider),
                                model=judge.model,
                                case=case,
                                transcript=transcript,
                                judge_mode=judge_mode,
                            )
                        except Exception as error:
                            error_text = f"Judge failed: {error}"
                            print(error_text)
                            evaluation = {"winner": "Judge error", "confidence": 0, "run_error": error_text}
                        judge_content = json.dumps(evaluation, indent=2, ensure_ascii=False)
                        judge_message = Message(speaker="Judge", role=f"{judge.provider}:{judge.model} {judge_mode} Evaluation", content=judge_content)
                        transcript.append(judge_message)
                        print_message(judge_message)
                        evaluations.append((judge, judge_mode, evaluation))

        transcript_json, transcript_markdown = save_transcript(
            transcript,
            run["question"],
            run_label=f"{run_id}_{run['label']}",
        )

        for judge, judge_mode, judge_result in evaluations:
            rows.append(
                make_row(
                    run_id=run_id,
                    debate_id=run["label"],
                    benchmark_mode=run["benchmark_mode"],
                    pair_id=run["pair_id"],
                    round_index=int(run["round_index"]),
                    topic_id=run["topic_id"],
                    question=run["question"],
                    position_a=run["position_a"],
                    position_b=run["position_b"],
                    provider="mixed" if run["position_a_provider"] != run["position_b_provider"] else run["position_a_provider"],
                    judge_model="" if args.no_judge else judge.model,
                    judge_provider="" if args.no_judge else judge.provider,
                    judge_mode=judge_mode,
                    role_assignment=run["role_assignment"],
                    start_style=run["start_style"],
                    position_a_model=run["position_a_model"],
                    position_a_provider=run["position_a_provider"],
                    position_b_model=run["position_b_model"],
                    position_b_provider=run["position_b_provider"],
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
