import argparse
import csv
import re
import subprocess
import sys
import time
from pathlib import Path

from generate_judgement_files import DEFAULT_JUDGES


DEFAULT_OUTPUT_DIR = Path("runs/2026-08-28_repeated_judgment_stability")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run repeated-judgment stability sequentially by judge."
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--judges", default=",".join(DEFAULT_JUDGES))
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--call-delay", type=float, default=10.0)
    parser.add_argument("--rate-limit-sleep", type=int, default=600)
    parser.add_argument("--idle-sleep", type=int, default=600)
    return parser.parse_args()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def row_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def main() -> None:
    args = parse_args()
    judges = [judge.strip() for judge in args.judges.split(",") if judge.strip()]
    expected = 240 * args.repeats
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for judge in judges:
        output = args.output_dir / f"judgements_{slug(judge)}.csv"
        while row_count(output) < expected:
            before = row_count(output)
            print(f"starting judge={judge} rows={before}/{expected}", flush=True)
            command = [
                sys.executable,
                "run_repeated_judgment_stability.py",
                "--judge",
                judge,
                "--output-dir",
                str(args.output_dir),
                "--repeats",
                str(args.repeats),
                "--call-delay",
                str(args.call_delay),
                "--rate-limit-sleep",
                str(args.rate_limit_sleep),
            ]
            result = subprocess.run(command, check=False)
            after = row_count(output)
            print(
                f"judge pass finished judge={judge} exit={result.returncode} "
                f"rows={after}/{expected}",
                flush=True,
            )
            if after <= before:
                time.sleep(args.idle_sleep)
            elif after < expected:
                time.sleep(60)

    print("All repeated-judgment stability files are complete.", flush=True)


if __name__ == "__main__":
    main()
