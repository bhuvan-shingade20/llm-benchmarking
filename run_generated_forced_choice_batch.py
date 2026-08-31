import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resume all six generated-debate judges.")
    parser.add_argument("--config", type=Path, default=Path("configs/extension_2026_08_29.json"))
    parser.add_argument("--raw", type=Path, default=Path("runs/2026-08-29_six_model_ideology/RawDebates.csv"))
    parser.add_argument(
        "--transcript-dir",
        type=Path,
        default=Path("runs/2026-08-29_six_model_ideology/transcripts"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("runs/2026-08-29_six_model_ideology/judgements"))
    parser.add_argument("--call-delay", type=float, default=10.0)
    parser.add_argument("--rate-limit-sleep", type=int, default=600)
    return parser.parse_args()


def slug(value: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def main() -> None:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    expected = int(config["generated_debates"]["expected_debates"])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    log_path = args.output_dir / "batch.log"
    models = config["models"][1:5] + [config["models"][5], config["models"][0]]
    for model in models:
        judge = model["spec"]
        output = args.output_dir / f"judgements_{slug(judge)}.csv"
        while count(output) < expected:
            before = count(output)
            command = [
                sys.executable,
                "run_generated_forced_choice.py",
                "--raw",
                str(args.raw),
                "--transcript-dir",
                str(args.transcript_dir),
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
            ]
            with log_path.open("a", encoding="utf-8") as log:
                log.write("\n>>> " + " ".join(command) + "\n")
                log.flush()
                code = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, text=True).returncode
                log.write(f"\n<<< exit={code} rows={count(output)}\n")
            if count(output) == before:
                time.sleep(args.rate_limit_sleep)
        print(f"complete judge={judge} rows={expected}", flush=True)


if __name__ == "__main__":
    main()
