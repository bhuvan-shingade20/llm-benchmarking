import csv
import json
import subprocess
import sys
import time
from pathlib import Path


STABILITY_DIR = Path("runs/2026-08-28_repeated_judgment_stability")
IDEOLOGY_DIR = Path("runs/2026-08-28_ideological_persuasion")
VALIDATED_TOPICS = IDEOLOGY_DIR / "annotation_analysis" / "validated_ideology_topics.json"
IDEOLOGY_DATASET = IDEOLOGY_DIR / "dataset"


def run(command: list[str]) -> int:
    print(">>> " + " ".join(command), flush=True)
    result = subprocess.run(command, check=False)
    print(f"<<< exit={result.returncode}", flush=True)
    return result.returncode


def completed_judge_cells(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return 0
    winner_fields = [field for field in rows[0] if field.endswith(" winner")]
    return sum(bool(row.get(field)) for row in rows for field in winner_fields)


def main() -> None:
    print("Stage 1/7: repeated-judgment stability", flush=True)
    run(
        [
            sys.executable,
            "run_repeated_judgment_stability_batch.py",
            "--call-delay",
            "10",
            "--rate-limit-sleep",
            "600",
            "--idle-sleep",
            "600",
        ]
    )

    print("Stage 2/7: stability analysis", flush=True)
    if run([sys.executable, "analyze_repeated_judgment_stability.py"]):
        raise RuntimeError("Stability analysis failed")

    print("Stage 3/7: blinded ideology annotations", flush=True)
    run(
        [
            sys.executable,
            "run_ideology_annotation_batch.py",
            "--call-delay",
            "10",
            "--rate-limit-sleep",
            "600",
            "--idle-sleep",
            "600",
        ]
    )

    print("Stage 4/7: annotation validation", flush=True)
    if run([sys.executable, "analyze_ideology_annotations.py"]):
        raise RuntimeError("Ideology annotation analysis failed")
    validated = json.loads(VALIDATED_TOPICS.read_text(encoding="utf-8"))
    if len(validated) != 20:
        raise RuntimeError(
            f"Only {len(validated)}/20 topics passed annotation. "
            "Replace rejected topics before debate generation."
        )

    print("Stage 5/7: ideological debate generation", flush=True)
    source = IDEOLOGY_DATASET / "RawDebates_modelAB_source.csv"
    final = IDEOLOGY_DATASET / "RawDebates.csv"
    transcripts = IDEOLOGY_DATASET / "transcripts"
    if run(
        [
            sys.executable,
            "run_full_rawdebates_batch.py",
            "--topics-file",
            str(VALIDATED_TOPICS),
            "--source",
            str(source),
            "--final",
            str(final),
            "--transcript-dir",
            str(transcripts),
            "--target-rows",
            "480",
            "--rounds",
            "8",
            "--max-tokens",
            "220",
            "--sleep-after-failure",
            "600",
        ]
    ):
        raise RuntimeError("Ideological debate generation failed")

    print("Stage 6/7: ideological cloud judgments", flush=True)
    judgment_dir = IDEOLOGY_DATASET / "judgements"
    diff_path = judgment_dir / "DiffPosJudgements.csv"
    expected_cells = 480 * 3
    while completed_judge_cells(diff_path) < expected_cells:
        before = completed_judge_cells(diff_path)
        run(
            [
                sys.executable,
                "generate_judgement_files.py",
                "--mode",
                "diff",
                "--raw",
                str(final),
                "--out-dir",
                str(judgment_dir),
                "--call-delay",
                "20",
                "--rate-limit-sleep",
                "600",
            ]
        )
        after = completed_judge_cells(diff_path)
        print(f"ideology judgment cells={after}/{expected_cells}", flush=True)
        time.sleep(600 if after <= before else 60)

    print("Stage 7/7: ideological persuasion analysis", flush=True)
    if run([sys.executable, "analyze_ideological_persuasion.py"]):
        raise RuntimeError("Ideological persuasion analysis failed")
    print("FOLLOW-UP EXPERIMENT PIPELINE COMPLETE", flush=True)


if __name__ == "__main__":
    main()
