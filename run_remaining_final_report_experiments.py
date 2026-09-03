import subprocess
import sys
import time
from pathlib import Path


EXP1 = Path("runs/2026-09-03_exp1_replication")
LOG = Path("runs/2026-09-03_final_report_queue.log")


def count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def exp1_complete() -> bool:
    if count_rows(EXP1 / "RawDebates.csv") != 840:
        return False
    for folder in ("different_position", "same_position"):
        files = list((EXP1 / folder).glob("judgements_*.csv"))
        if len(files) != 6 or any(count_rows(path) != 840 for path in files):
            return False
    return True


def run(command: list[str]) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as log:
        log.write("\n>>> " + " ".join(command) + "\n")
        log.flush()
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, text=True)
        log.write(f"\n<<< exit={result.returncode}\n")
    if result.returncode:
        raise SystemExit(result.returncode)


def main() -> None:
    while not exp1_complete():
        time.sleep(300)
    run([sys.executable, "analyze_experiment_1.py"])
    run([sys.executable, "run_experiment_2_batch.py"])
    run([sys.executable, "analyze_experiment_2_robustness.py"])
    run([sys.executable, "run_experiment_3.py"])
    run([sys.executable, "run_experiment_4.py"])


if __name__ == "__main__":
    main()
