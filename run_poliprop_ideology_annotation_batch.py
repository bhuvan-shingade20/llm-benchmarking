import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resume all PoliProp ideology annotators.")
    parser.add_argument("--config", type=Path, default=Path("configs/extension_2026_08_29.json"))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("runs/2026-08-29_poliprop_ideology_annotations"),
    )
    parser.add_argument("--call-delay", type=float, default=10.0)
    parser.add_argument("--rate-limit-sleep", type=int, default=600)
    return parser.parse_args()


def slug(value: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def row_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def main() -> None:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    log_path = args.output_dir / "batch.log"
    for annotator in config["ideology_annotators"]:
        output = args.output_dir / f"annotations_{slug(annotator)}.csv"
        while row_count(output) < 833:
            before = row_count(output)
            command = [
                sys.executable,
                "annotate_poliprop_ideology.py",
                "--config",
                str(args.config),
                "--output-dir",
                str(args.output_dir),
                "--annotator",
                annotator,
                "--call-delay",
                str(args.call_delay),
                "--rate-limit-sleep",
                str(args.rate_limit_sleep),
            ]
            with log_path.open("a", encoding="utf-8") as log:
                log.write("\n>>> " + " ".join(command) + "\n")
                log.flush()
                exit_code = subprocess.run(
                    command, stdout=log, stderr=subprocess.STDOUT, text=True
                ).returncode
                log.write(f"\n<<< exit={exit_code} rows={row_count(output)}\n")
            if row_count(output) == before:
                time.sleep(args.rate_limit_sleep)
        print(f"complete annotator={annotator} rows=833", flush=True)


if __name__ == "__main__":
    main()
