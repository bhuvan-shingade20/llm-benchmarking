import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


CONFIG = Path("configs/experiment_1_replication_2026_09_03.json")
OUTPUT_DIR = Path("runs/2026-09-03_exp2_robustness")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run all Experiment 2 judge streams resumably.")
    parser.add_argument("--call-delay", type=float, default=10.0)
    parser.add_argument("--rate-limit-sleep", type=int, default=600)
    return parser.parse_args()


def count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def slug(value: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def main() -> None:
    args = parse_args()
    panel = json.loads(CONFIG.read_text(encoding="utf-8"))
    expected = 120 * 5
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for model in panel["models"]:
        judge = model["spec"]
        output = OUTPUT_DIR / f"judgements_{slug(judge)}.csv"
        while count_rows(output) < expected:
            before = count_rows(output)
            command = [
                sys.executable,
                "run_experiment_2_robustness.py",
                "--judge",
                judge,
                "--call-delay",
                str(args.call_delay),
                "--rate-limit-sleep",
                str(args.rate_limit_sleep),
            ]
            with (OUTPUT_DIR / "batch.log").open("a", encoding="utf-8") as log:
                result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, text=True)
            if count_rows(output) <= before:
                time.sleep(args.rate_limit_sleep)
            if result.returncode and count_rows(output) <= before:
                continue


if __name__ == "__main__":
    main()
