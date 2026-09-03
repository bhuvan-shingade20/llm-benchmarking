import argparse
import json
import subprocess
import sys
from pathlib import Path


CONFIG = Path("configs/experiment_3_political_alignment_2026_09_03.json")
RUN_DIR = Path("runs/2026-09-03_exp3_political_alignment")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Experiment 3 resumably.")
    parser.add_argument("--call-delay", type=float, default=10.0)
    parser.add_argument("--rate-limit-sleep", type=int, default=600)
    return parser.parse_args()


def run(command: list[str]) -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    with (RUN_DIR / "experiment.log").open("a", encoding="utf-8") as log:
        log.write("\n>>> " + " ".join(command) + "\n")
        log.flush()
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, text=True)
        log.write(f"\n<<< exit={result.returncode}\n")
    if result.returncode:
        raise SystemExit(result.returncode)


def main() -> None:
    args = parse_args()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    annotations = RUN_DIR / "annotations"
    analysis = RUN_DIR / "annotation_analysis"
    run(
        [
            sys.executable,
            "run_ideology_annotation_batch.py",
            "--config",
            str(CONFIG),
            "--output-dir",
            str(annotations),
            "--call-delay",
            str(args.call_delay),
            "--rate-limit-sleep",
            str(args.rate_limit_sleep),
        ]
    )
    run(
        [
            sys.executable,
            "analyze_ideology_annotations.py",
            "--config",
            str(CONFIG),
            "--topics",
            config["generated_debates"]["topics_file"],
            "--input-dir",
            str(annotations),
            "--output-dir",
            str(analysis),
        ]
    )
    summary = json.loads((analysis / "analysis_summary.json").read_text(encoding="utf-8"))
    if summary["accepted_topics"] != config["generated_debates"]["topic_count"]:
        raise SystemExit(
            "Political topic validation did not accept all ten frozen topics; generation is blocked."
        )

    models = ",".join(model["spec"] for model in config["models"])
    raw = RUN_DIR / "RawDebates.csv"
    transcripts = RUN_DIR / "transcripts"
    run(
        [
            sys.executable,
            "run_full_rawdebates_batch.py",
            "--source",
            str(RUN_DIR / "RawDebates_modelAB_source.csv"),
            "--final",
            str(raw),
            "--transcript-dir",
            str(transcripts),
            "--topics-file",
            config["generated_debates"]["topics_file"],
            "--topics",
            *config["generated_debates"]["topic_ids"],
            "--models",
            models,
            "--target-rows",
            str(config["generated_debates"]["expected_debates"]),
            "--rounds",
            str(config["generated_debates"]["messages_per_debate"]),
            "--max-tokens",
            str(config["generated_debates"]["max_tokens_per_message"]),
            "--sleep-after-failure",
            str(args.rate_limit_sleep),
        ]
    )
    run(
        [
            sys.executable,
            "run_generated_forced_choice_batch.py",
            "--config",
            str(CONFIG),
            "--raw",
            str(raw),
            "--transcript-dir",
            str(transcripts),
            "--output-dir",
            str(RUN_DIR / "judgements"),
            "--call-delay",
            str(args.call_delay),
            "--rate-limit-sleep",
            str(args.rate_limit_sleep),
        ]
    )
    run(
        [
            sys.executable,
            "analyze_six_model_ideology.py",
            "--raw",
            str(raw),
            "--judgements",
            str(RUN_DIR / "judgements"),
            "--topics",
            config["generated_debates"]["topics_file"],
            "--config",
            str(CONFIG),
        ]
    )


if __name__ == "__main__":
    main()
