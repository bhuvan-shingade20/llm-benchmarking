import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path


DEFAULT_CONFIG = Path("configs/extension_2026_08_29.json")
DEFAULT_OUTPUT_DIR = Path("runs/2026-08-29_real_world_forced_choice_v2")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resume all six real-world judge streams sequentially.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--call-delay", type=float, default=10.0)
    parser.add_argument("--rate-limit-sleep", type=int, default=600)
    parser.add_argument(
        "--condition-set",
        choices=("primary", "robustness", "all"),
        default="all",
    )
    return parser.parse_args()


def slug(value: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def rows(path: Path, condition_set: str = "all") -> int:
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8") as handle:
        records = list(csv.DictReader(handle))
    if condition_set == "all":
        return len(records)
    primary = lambda row: (
        row["PromptVersion"] == "canonical"
        and row["PresentationOrder"] == "pro_first"
        and row["RepeatIndex"] == "1"
    )
    return sum(
        1
        for row in records
        if primary(row) == (condition_set == "primary")
    )


def main() -> None:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    log_path = args.output_dir / "batch.log"
    models = config["models"][1:5] + [config["models"][5], config["models"][0]]
    expected = {"primary": 740, "robustness": 480, "all": 1220}[
        args.condition_set
    ]
    for model in models:
        judge = model["spec"]
        output = args.output_dir / f"judgements_{slug(judge)}.csv"
        while rows(output, args.condition_set) < expected:
            before = rows(output, args.condition_set)
            command = [
                sys.executable,
                "run_real_world_forced_choice.py",
                "--config",
                str(args.config),
                "--output-dir",
                str(args.output_dir),
                "--judge",
                judge,
                "--call-delay",
                str(args.call_delay),
                "--rate-limit-sleep",
                str(args.rate_limit_sleep),
                "--condition-set",
                args.condition_set,
            ]
            with log_path.open("a", encoding="utf-8") as log:
                log.write("\n>>> " + " ".join(command) + "\n")
                log.flush()
                exit_code = subprocess.run(
                    command, stdout=log, stderr=subprocess.STDOUT, text=True
                ).returncode
                log.write(
                    f"\n<<< exit={exit_code} "
                    f"{args.condition_set}_rows={rows(output, args.condition_set)}\n"
                )
            after = rows(output, args.condition_set)
            if after == before:
                time.sleep(args.rate_limit_sleep)
        print(
            f"complete judge={judge} condition_set={args.condition_set} rows={expected}",
            flush=True,
        )


if __name__ == "__main__":
    main()
