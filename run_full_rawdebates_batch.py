import argparse
import csv
import subprocess
import sys
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resumable batch runner for the paper RawDebates.csv file.")
    parser.add_argument("--source", required=True, help="ModelA/ModelB source CSV path.")
    parser.add_argument("--final", required=True, help="Final Model1/Model2 RawDebates.csv path.")
    parser.add_argument("--transcript-dir", required=True, help="Transcript directory.")
    parser.add_argument("--topics-file", default="topics/phase1_topics.json", help="Topic JSON file.")
    parser.add_argument(
        "--models",
        help="Comma-separated provider:model specs passed to generate_clean_rawdebates.py.",
    )
    parser.add_argument(
        "--topics",
        nargs="*",
        help="Optional topic ids to generate; omit to use every topic in --topics-file.",
    )
    parser.add_argument("--target-rows", type=int, default=240, help="Stop after this many source rows.")
    parser.add_argument("--rounds", type=int, default=8, help="Alternating messages per debate.")
    parser.add_argument("--max-tokens", type=int, default=220, help="Max tokens per message.")
    parser.add_argument("--sleep-after-failure", type=int, default=180, help="Seconds to wait after failed subprocess.")
    return parser.parse_args()


def row_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def run_command(command: list[str], log_path: Path) -> int:
    with log_path.open("a", encoding="utf-8") as log:
        log.write("\n\n>>> " + " ".join(command) + "\n")
        log.flush()
        process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, text=True)
        log.write(f"\n<<< exit={process.returncode}\n")
        return process.returncode


def main() -> None:
    args = parse_args()
    source = Path(args.source)
    final = Path(args.final)
    log_path = final.parent / "generation.log"
    source.parent.mkdir(parents=True, exist_ok=True)
    final.parent.mkdir(parents=True, exist_ok=True)

    topic_args = [
        arg for topic_id in (args.topics or []) for arg in ("--topic-id", topic_id)
    ]
    while row_count(source) < args.target_rows:
        before = row_count(source)
        generate_command = [
            sys.executable,
            "generate_clean_rawdebates.py",
            "--topics",
            str(args.topics_file),
            *topic_args,
            "--rounds",
            str(args.rounds),
            "--max-tokens",
            str(args.max_tokens),
            "--output",
            str(source),
            "--transcript-dir",
            str(args.transcript_dir),
            "--max-new-debates",
            "1",
        ]
        if args.models:
            generate_command.extend(["--models", args.models])
        exit_code = run_command(generate_command, log_path)
        after = row_count(source)
        if after > before:
            convert_command = [
                sys.executable,
                "convert_rawdebates_model_slots.py",
                "--input",
                str(source),
                "--output",
                str(final),
            ]
            run_command(convert_command, log_path)
        if exit_code != 0 or after == before:
            time.sleep(args.sleep_after_failure)
        else:
            time.sleep(5)

    run_command(
        [
            sys.executable,
            "convert_rawdebates_model_slots.py",
            "--input",
            str(source),
            "--output",
            str(final),
        ],
        log_path,
    )


if __name__ == "__main__":
    main()
