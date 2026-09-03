import argparse
import json
import subprocess
import sys
from pathlib import Path


CONFIG = Path("configs/experiment_1_replication_2026_09_03.json")
RUN_DIR = Path("runs/2026-09-03_exp1_replication")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Experiment 1 resumably.")
    parser.add_argument(
        "--from-stage",
        choices=("generation", "different_position", "same_position"),
        default="generation",
    )
    parser.add_argument("--call-delay", type=float, default=10.0)
    parser.add_argument("--rate-limit-sleep", type=int, default=600)
    return parser.parse_args()


def run(command: list[str], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log:
        log.write("\n>>> " + " ".join(command) + "\n")
        log.flush()
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, text=True)
        log.write(f"\n<<< exit={result.returncode}\n")
    if result.returncode:
        raise SystemExit(result.returncode)


def main() -> None:
    args = parse_args()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    stages = ("generation", "different_position", "same_position")
    start = stages.index(args.from_stage)
    models = ",".join(model["spec"] for model in config["models"])
    raw = RUN_DIR / "RawDebates.csv"
    transcripts = RUN_DIR / "transcripts"
    RUN_DIR.mkdir(parents=True, exist_ok=True)

    if start <= 0:
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
            ],
            RUN_DIR / "experiment.log",
        )
    if start <= 1:
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
                str(RUN_DIR / "different_position"),
                "--call-delay",
                str(args.call_delay),
                "--rate-limit-sleep",
                str(args.rate_limit_sleep),
            ],
            RUN_DIR / "experiment.log",
        )
    if start <= 2:
        run(
            [
                sys.executable,
                "run_same_position_forced_choice_batch.py",
                "--config",
                str(CONFIG),
                "--raw",
                str(raw),
                "--output-dir",
                str(RUN_DIR / "same_position"),
                "--call-delay",
                str(args.call_delay),
                "--rate-limit-sleep",
                str(args.rate_limit_sleep),
            ],
            RUN_DIR / "experiment.log",
        )


if __name__ == "__main__":
    main()
