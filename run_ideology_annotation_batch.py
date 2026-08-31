import argparse
import csv
import re
import subprocess
import sys
import time
from pathlib import Path

from annotate_ideology_topics import DEFAULT_ANNOTATORS


DEFAULT_OUTPUT_DIR = Path("runs/2026-08-28_ideological_persuasion/annotations")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ideology annotators sequentially and resumably.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--annotators", default=",".join(DEFAULT_ANNOTATORS))
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
    annotators = [item.strip() for item in args.annotators.split(",") if item.strip()]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for annotator in annotators:
        output = args.output_dir / f"annotations_{slug(annotator)}.csv"
        while row_count(output) < 20:
            before = row_count(output)
            print(f"starting annotator={annotator} rows={before}/20", flush=True)
            result = subprocess.run(
                [
                    sys.executable,
                    "annotate_ideology_topics.py",
                    "--annotator",
                    annotator,
                    "--output-dir",
                    str(args.output_dir),
                    "--call-delay",
                    str(args.call_delay),
                    "--rate-limit-sleep",
                    str(args.rate_limit_sleep),
                ],
                check=False,
            )
            after = row_count(output)
            print(
                f"annotator pass finished annotator={annotator} exit={result.returncode} "
                f"rows={after}/20",
                flush=True,
            )
            if after <= before:
                time.sleep(args.idle_sleep)
            elif after < 20:
                time.sleep(60)
    print("All ideological annotation files are complete.", flush=True)


if __name__ == "__main__":
    main()
