import argparse
import subprocess
import sys
from pathlib import Path


CONFIG = Path("configs/extension_2026_08_29.json")
RUN_DIR = Path("runs/2026-08-29_real_world_forced_choice_v2")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Complete Experiment 4 resumably.")
    parser.add_argument("--call-delay", type=float, default=10.0)
    parser.add_argument("--rate-limit-sleep", type=int, default=600)
    return parser.parse_args()


def run(command: list[str]) -> None:
    with (RUN_DIR / "experiment_4.log").open("a", encoding="utf-8") as log:
        log.write("\n>>> " + " ".join(command) + "\n")
        log.flush()
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, text=True)
        log.write(f"\n<<< exit={result.returncode}\n")
    if result.returncode:
        raise SystemExit(result.returncode)


def main() -> None:
    args = parse_args()
    run(
        [
            sys.executable,
            "run_real_world_forced_choice_batch.py",
            "--config",
            str(CONFIG),
            "--output-dir",
            str(RUN_DIR),
            "--condition-set",
            "primary",
            "--call-delay",
            str(args.call_delay),
            "--rate-limit-sleep",
            str(args.rate_limit_sleep),
        ]
    )
    run(
        [
            sys.executable,
            "analyze_real_world_forced_choice.py",
            "--results-dir",
            str(RUN_DIR),
            "--primary-only",
        ]
    )


if __name__ == "__main__":
    main()
