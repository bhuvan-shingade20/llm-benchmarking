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
    EVALUATION_PROTOCOLS,
    JUDGE_MODES,
    SPEAKER_ORDERS,
    START_PROMPTS,
    DiscussionCase,
    Message,
    ModelSpec,
    build_client,
    judge_conversation,
    judge_same_position_comparison,
    load_topics,
    make_discussion_case,
    model_label,
    parse_model_spec,
    print_message,
    run_conversation,
    save_transcript,
    transcript_debate_text,
)


RESULTS_DIR = Path("results")
BENCHMARK_MODES = {"single", "paired", "permutations", "same_position"}
BENCHMARK_SPEAKER_ORDERS = {"a_first", "b_first", "balanced"}


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
    evaluation_protocol: str,
    role_assignment: str,
    start_style: str,
    speaker_order: str,
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
        "speaker_order": speaker_order,
        "position_a_provider": position_a_provider,
        "position_a_model": position_a_model,
        "position_b_provider": position_b_provider,
        "position_b_model": position_b_model,
        "judge_provider": judge_provider,
        "judge_model": judge_model,
        "judge_mode": judge_mode,
        "evaluation_protocol": evaluation_protocol,
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
    speaker_orders: list[str],
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
            for speaker_order in speaker_orders:
                for pair in model_pairs:
                    label = f"{case.id}_{benchmark_mode}_{start_style}_{speaker_order}_{pair['pair_id']}_r{pair['round_index']}"
                    runs.append(
                        {
                            "topic_id": case.id or "",
                            "question": case.question,
                            "position_a": case.position_a,
                            "position_b": case.position_b,
                            "benchmark_mode": benchmark_mode,
                            "role_assignment": pair["role_assignment"],
                            "start_style": start_style,
                            "speaker_order": speaker_order,
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


def build_same_position_comparisons(
    cases: list[DiscussionCase],
    fixed_opponent: ModelSpec,
    candidates: list[ModelSpec],
    start_styles: list[str],
    speaker_orders: list[str],
    candidate_position: str,
) -> list[dict[str, Any]]:
    if len(candidates) < 2:
        raise SystemExit("same_position mode requires at least two candidate models in --models.")
    if candidate_position not in {"position_a", "position_b"}:
        raise SystemExit("--same-position-target must be position_a or position_b.")

    comparisons: list[dict[str, Any]] = []
    candidate_pairs = [
        (left, right)
        for left_index, left in enumerate(candidates)
        for right in candidates[left_index + 1 :]
    ]
    for case in cases:
        for start_style in start_styles:
            for speaker_order in speaker_orders:
                for pair_index, (candidate_1, candidate_2) in enumerate(candidate_pairs, start=1):
                    pair_id = f"pair{pair_index:02d}"
                    label = f"{case.id}_same_position_{candidate_position}_{start_style}_{speaker_order}_{pair_id}"
                    if candidate_position == "position_b":
                        candidate_1_run = {
                            "position_a_provider": fixed_opponent.provider,
                            "position_a_model": fixed_opponent.model,
                            "position_b_provider": candidate_1.provider,
                            "position_b_model": candidate_1.model,
                        }
                        candidate_2_run = {
                            "position_a_provider": fixed_opponent.provider,
                            "position_a_model": fixed_opponent.model,
                            "position_b_provider": candidate_2.provider,
                            "position_b_model": candidate_2.model,
                        }
                    else:
                        candidate_1_run = {
                            "position_a_provider": candidate_1.provider,
                            "position_a_model": candidate_1.model,
                            "position_b_provider": fixed_opponent.provider,
                            "position_b_model": fixed_opponent.model,
                        }
                        candidate_2_run = {
                            "position_a_provider": candidate_2.provider,
                            "position_a_model": candidate_2.model,
                            "position_b_provider": fixed_opponent.provider,
                            "position_b_model": fixed_opponent.model,
                        }

                    comparisons.append(
                        {
                            "topic_id": case.id or "",
                            "question": case.question,
                            "position_a": case.position_a,
                            "position_b": case.position_b,
                            "benchmark_mode": "same_position",
                            "role_assignment": f"same_position_{candidate_position}",
                            "candidate_position": candidate_position,
                            "start_style": start_style,
                            "speaker_order": speaker_order,
                            "candidate_1_provider": candidate_1.provider,
                            "candidate_1_model": candidate_1.model,
                            "candidate_2_provider": candidate_2.provider,
                            "candidate_2_model": candidate_2.model,
                            "fixed_opponent_provider": fixed_opponent.provider,
                            "fixed_opponent_model": fixed_opponent.model,
                            "candidate_1_run": candidate_1_run,
                            "candidate_2_run": candidate_2_run,
                            "pair_id": pair_id,
                            "round_index": "1",
                            "label": label,
                        }
                    )
    return comparisons


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
        "--evaluation-protocol",
        default="holistic_persuasion",
        choices=["all", *sorted(EVALUATION_PROTOCOLS)],
        help="Evaluation protocol for judging. Use all to apply all four protocols to the same transcript.",
    )
    parser.add_argument(
        "--evaluation-protocols",
        default=os.getenv("EVALUATION_PROTOCOLS", ""),
        help="Comma-separated evaluation protocols. Use all for every protocol.",
    )
    parser.add_argument(
        "--benchmark-mode",
        "--mode",
        dest="benchmark_mode",
        choices=sorted(BENCHMARK_MODES),
        help="single/paired/permutations judge one transcript; same_position compares two same-position candidates across separate debates.",
    )
    parser.add_argument(
        "--same-position-target",
        default="position_b",
        choices=["position_a", "position_b"],
        help="For same_position mode, choose whether candidate models argue Position A or Position B against the fixed --model-a opponent.",
    )
    parser.add_argument("--turns", type=int, default=4, help="Debate turns before closing statements.")
    parser.add_argument("--max-tokens", type=int, default=220, help="Maximum tokens per debate turn.")
    parser.add_argument("--limit", type=int, help="Limit number of topics for quick tests.")
    parser.add_argument(
        "--start-styles",
        default="neutral",
        help=f"Comma-separated moderator start styles. Available: {', '.join(sorted(START_PROMPTS))}.",
    )
    parser.add_argument(
        "--speaker-order",
        default=os.getenv("SPEAKER_ORDER", "balanced"),
        choices=sorted(BENCHMARK_SPEAKER_ORDERS),
        help="Use a_first, b_first, or balanced to run both orders and control first/last speaker bias.",
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
    speaker_orders = sorted(SPEAKER_ORDERS) if args.speaker_order == "balanced" else [args.speaker_order]

    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{os.getpid()}_benchmark"
    if benchmark_mode == "same_position":
        planned_runs = build_same_position_comparisons(
            cases=cases,
            fixed_opponent=model_a,
            candidates=models,
            start_styles=start_styles,
            speaker_orders=speaker_orders,
            candidate_position=args.same_position_target,
        )
    else:
        planned_runs = build_runs(
            cases=cases,
            model_a=model_a,
            model_b=model_b,
            models=models,
            start_styles=start_styles,
            benchmark_mode=benchmark_mode,
            speaker_orders=speaker_orders,
        )

    judge_modes = [] if args.no_judge else (["winner_only", "detailed"] if args.judge_mode == "both" else [args.judge_mode])
    requested_protocols = parse_csv_list(args.evaluation_protocols) or [args.evaluation_protocol]
    evaluation_protocols = sorted(EVALUATION_PROTOCOLS) if "all" in requested_protocols else requested_protocols
    invalid_protocols = [protocol for protocol in evaluation_protocols if protocol not in EVALUATION_PROTOCOLS]
    if invalid_protocols:
        raise SystemExit(f"Invalid evaluation protocol(s): {', '.join(invalid_protocols)}")

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
        print(f"Evaluation protocol(s): {', '.join(evaluation_protocols)}")
    print(f"Start styles: {', '.join(start_styles)}")
    print(f"Speaker order: {args.speaker_order} ({', '.join(speaker_orders)})")
    planned_debates = len(planned_runs) * 2 if benchmark_mode == "same_position" else len(planned_runs)
    print(f"Topics: {len(cases)} | Planned debates: {planned_debates}")
    if judge_modes:
        print(f"Planned judge evaluations: {len(planned_runs) * len(judge_modes) * len(judge_models) * len(evaluation_protocols)}")

    if args.dry_run:
        for index, run in enumerate(planned_runs, start=1):
            if benchmark_mode == "same_position":
                first = run["candidate_1_run"]
                second = run["candidate_2_run"]
                print(
                    f"{index}. {run['label']} | fixed_opponent={run['fixed_opponent_provider']}:{run['fixed_opponent_model']} | "
                    f"candidate_position={run['candidate_position']} | candidate_1={run['candidate_1_provider']}:{run['candidate_1_model']} | "
                    f"candidate_2={run['candidate_2_provider']}:{run['candidate_2_model']} | speaker_order={run['speaker_order']} | start={run['start_style']}"
                )
                print(
                    f"   debate A: Position A={first['position_a_provider']}:{first['position_a_model']} | "
                    f"Position B={first['position_b_provider']}:{first['position_b_model']}"
                )
                print(
                    f"   debate B: Position A={second['position_a_provider']}:{second['position_a_model']} | "
                    f"Position B={second['position_b_provider']}:{second['position_b_model']} | {run['question']}"
                )
            else:
                print(
                    f"{index}. {run['label']} | Position A={run['position_a_provider']}:{run['position_a_model']} | "
                    f"Position B={run['position_b_provider']}:{run['position_b_model']} | mode={run['benchmark_mode']} | "
                    f"round={run['round_index']} | speaker_order={run['speaker_order']} | start={run['start_style']} | {run['question']}"
                )
        return

    rows: list[dict[str, Any]] = []
    client_cache: dict[str, Any] = {}

    def get_client(provider: str) -> Any:
        if provider not in client_cache:
            client_cache[provider] = build_client(provider)
        return client_cache[provider]

    if benchmark_mode == "same_position":
        for index, run in enumerate(planned_runs, start=1):
            print(f"\n=== Same-position comparison {index}/{len(planned_runs)}: {run['label']} ===")
            print(f"Question: {run['question']}")
            print(f"Target candidate position: {run['candidate_position']}")
            print(f"Fixed opponent: {run['fixed_opponent_provider']}:{run['fixed_opponent_model']}")
            print(f"Candidate 1: {run['candidate_1_provider']}:{run['candidate_1_model']}")
            print(f"Candidate 2: {run['candidate_2_provider']}:{run['candidate_2_model']}")
            print(f"Start style: {run['start_style']} | Speaker order: {run['speaker_order']}")

            comparison_transcript: list[Message] = [
                Message(speaker="System", role="Same-position Comparison", content=f"Discussion question: {run['question']}"),
            ]
            evaluations: list[tuple[ModelSpec, str, str, dict[str, Any]]] = []
            try:
                candidate_1_run = run["candidate_1_run"]
                candidate_2_run = run["candidate_2_run"]
                candidate_1_transcript = run_conversation(
                    topic=run["question"],
                    turns=args.turns,
                    provider=args.provider,
                    model_a=candidate_1_run["position_a_model"],
                    model_b=candidate_1_run["position_b_model"],
                    judge_model=judge_models[0].model,
                    judge_enabled=False,
                    max_tokens=args.max_tokens,
                    position_a=run["position_a"],
                    position_b=run["position_b"],
                    start_style=run["start_style"],
                    provider_a=candidate_1_run["position_a_provider"],
                    provider_b=candidate_1_run["position_b_provider"],
                    judge_provider=judge_models[0].provider,
                    speaker_order=run["speaker_order"],
                )
                candidate_2_transcript = run_conversation(
                    topic=run["question"],
                    turns=args.turns,
                    provider=args.provider,
                    model_a=candidate_2_run["position_a_model"],
                    model_b=candidate_2_run["position_b_model"],
                    judge_model=judge_models[0].model,
                    judge_enabled=False,
                    max_tokens=args.max_tokens,
                    position_a=run["position_a"],
                    position_b=run["position_b"],
                    start_style=run["start_style"],
                    provider_a=candidate_2_run["position_a_provider"],
                    provider_b=candidate_2_run["position_b_provider"],
                    judge_provider=judge_models[0].provider,
                    speaker_order=run["speaker_order"],
                )
            except Exception as error:
                error_text = f"Conversation failed: {error}"
                print(error_text)
                comparison_transcript.append(Message(speaker="System", role="Run Error", content=error_text))
                evaluations.append((ModelSpec(provider="", model=""), "", "", {"winner": "Run error", "confidence": 0, "run_error": error_text}))
            else:
                comparison_transcript.extend(
                    [
                        Message(speaker="System", role="Candidate 1 Transcript", content=transcript_debate_text(candidate_1_transcript)),
                        Message(speaker="System", role="Candidate 2 Transcript", content=transcript_debate_text(candidate_2_transcript)),
                    ]
                )
                if args.no_judge:
                    evaluations.append((ModelSpec(provider="", model=""), "", "", {"winner": "No judge", "confidence": 0}))
                else:
                    case = make_discussion_case(
                        run["question"],
                        position_a=run["position_a"],
                        position_b=run["position_b"],
                        case_id=run["topic_id"],
                    )
                    for judge in judge_models:
                        for judge_mode in judge_modes:
                            for evaluation_protocol in evaluation_protocols:
                                try:
                                    evaluation = judge_same_position_comparison(
                                        client=get_client(judge.provider),
                                        model=judge.model,
                                        case=case,
                                        candidate_position=run["candidate_position"],
                                        candidate_1_label=f"{run['candidate_1_provider']}:{run['candidate_1_model']}",
                                        candidate_1_transcript=candidate_1_transcript,
                                        candidate_2_label=f"{run['candidate_2_provider']}:{run['candidate_2_model']}",
                                        candidate_2_transcript=candidate_2_transcript,
                                        judge_mode=judge_mode,
                                        evaluation_protocol=evaluation_protocol,
                                    )
                                except Exception as error:
                                    error_text = f"Judge failed: {error}"
                                    print(error_text)
                                    evaluation = {"winner": "Judge error", "confidence": 0, "run_error": error_text}
                                judge_content = json.dumps(evaluation, indent=2, ensure_ascii=False)
                                judge_message = Message(
                                    speaker="Judge",
                                    role=f"{judge.provider}:{judge.model} same_position {judge_mode} {evaluation_protocol} Evaluation",
                                    content=judge_content,
                                )
                                comparison_transcript.append(judge_message)
                                print_message(judge_message)
                                evaluations.append((judge, judge_mode, evaluation_protocol, evaluation))

            transcript_json, transcript_markdown = save_transcript(
                comparison_transcript,
                run["question"],
                run_label=f"{run_id}_{run['label']}",
            )
            target_position = run["position_a"] if run["candidate_position"] == "position_a" else run["position_b"]
            for judge, judge_mode, evaluation_protocol, judge_result in evaluations:
                row = make_row(
                    run_id=run_id,
                    debate_id=run["label"],
                    benchmark_mode=run["benchmark_mode"],
                    pair_id=run["pair_id"],
                    round_index=int(run["round_index"]),
                    topic_id=run["topic_id"],
                    question=run["question"],
                    position_a=target_position,
                    position_b=target_position,
                    provider="mixed" if run["candidate_1_provider"] != run["candidate_2_provider"] else run["candidate_1_provider"],
                    judge_model="" if args.no_judge else judge.model,
                    judge_provider="" if args.no_judge else judge.provider,
                    judge_mode=judge_mode,
                    evaluation_protocol=evaluation_protocol,
                    role_assignment=run["role_assignment"],
                    start_style=run["start_style"],
                    speaker_order=run["speaker_order"],
                    position_a_model=run["candidate_1_model"],
                    position_a_provider=run["candidate_1_provider"],
                    position_b_model=run["candidate_2_model"],
                    position_b_provider=run["candidate_2_provider"],
                    transcript_json=transcript_json,
                    transcript_markdown=transcript_markdown,
                    judge_result=judge_result,
                )
                row.update(
                    {
                        "comparison_type": "same_position",
                        "candidate_position": run["candidate_position"],
                        "fixed_opponent_provider": run["fixed_opponent_provider"],
                        "fixed_opponent_model": run["fixed_opponent_model"],
                        "candidate_1_provider": run["candidate_1_provider"],
                        "candidate_1_model": run["candidate_1_model"],
                        "candidate_2_provider": run["candidate_2_provider"],
                        "candidate_2_model": run["candidate_2_model"],
                    }
                )
                rows.append(row)

            results_json, results_csv = write_results(rows, run_id)
            print(f"Partial results saved: {results_csv}")

        results_json, results_csv = write_results(rows, run_id)
        print("\nBenchmark completed")
        print(f"Results JSON: {results_json}")
        print(f"Results CSV: {results_csv}")
        return

    for index, run in enumerate(planned_runs, start=1):
        print(f"\n=== Debate {index}/{len(planned_runs)}: {run['label']} ===")
        print(f"Question: {run['question']}")
        print(f"Benchmark mode: {run['benchmark_mode']} | Pair: {run['pair_id']} | Round: {run['round_index']}")
        print(f"Start style: {run['start_style']}")
        print(f"Speaker order: {run['speaker_order']}")
        print(f"Position A model: {run['position_a_provider']}:{run['position_a_model']}")
        print(f"Position B model: {run['position_b_provider']}:{run['position_b_model']}")

        evaluations: list[tuple[ModelSpec, str, str, dict[str, Any]]] = []
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
                speaker_order=run["speaker_order"],
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
                    "",
                    {"winner": "Run error", "confidence": 0, "run_error": error_text},
                )
            )
        else:
            if args.no_judge:
                evaluations.append((ModelSpec(provider="", model=""), "", "", {"winner": "No judge", "confidence": 0}))
            else:
                case = make_discussion_case(
                    run["question"],
                    position_a=run["position_a"],
                    position_b=run["position_b"],
                    case_id=run["topic_id"],
                )
                for judge in judge_models:
                    for judge_mode in judge_modes:
                        for evaluation_protocol in evaluation_protocols:
                            try:
                                evaluation = judge_conversation(
                                    client=get_client(judge.provider),
                                    model=judge.model,
                                    case=case,
                                    transcript=transcript,
                                    judge_mode=judge_mode,
                                    evaluation_protocol=evaluation_protocol,
                                )
                            except Exception as error:
                                error_text = f"Judge failed: {error}"
                                print(error_text)
                                evaluation = {"winner": "Judge error", "confidence": 0, "run_error": error_text}
                            judge_content = json.dumps(evaluation, indent=2, ensure_ascii=False)
                            judge_message = Message(
                                speaker="Judge",
                                role=f"{judge.provider}:{judge.model} {judge_mode} {evaluation_protocol} Evaluation",
                                content=judge_content,
                            )
                            transcript.append(judge_message)
                            print_message(judge_message)
                            evaluations.append((judge, judge_mode, evaluation_protocol, evaluation))

        transcript_json, transcript_markdown = save_transcript(
            transcript,
            run["question"],
            run_label=f"{run_id}_{run['label']}",
        )

        for judge, judge_mode, evaluation_protocol, judge_result in evaluations:
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
                    evaluation_protocol=evaluation_protocol,
                    role_assignment=run["role_assignment"],
                    start_style=run["start_style"],
                    speaker_order=run["speaker_order"],
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
