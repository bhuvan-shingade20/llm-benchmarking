import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


CONFIG = Path("configs/extension_2026_08_29.json")
PIPELINE_DIR = Path("runs/2026-08-29_extension_pipeline")
REAL_RESULTS = Path("runs/2026-08-29_real_world_forced_choice_v2")
ANNOTATIONS = Path("runs/2026-08-29_poliprop_ideology_annotations")
GENERATED = Path("runs/2026-08-29_six_model_ideology")


def run(command: list[str], log) -> None:
    log.write(f"\n[{datetime.now(timezone.utc).isoformat()}] >>> {' '.join(command)}\n")
    log.flush()
    code = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, text=True).returncode
    log.write(f"\n[{datetime.now(timezone.utc).isoformat()}] <<< exit={code}\n")
    log.flush()
    if code:
        raise RuntimeError(f"Pipeline stage failed with exit code {code}: {' '.join(command)}")


def main() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    available_first = config["models"][1:5] + [config["models"][5], config["models"][0]]
    models = ",".join(model["spec"] for model in available_first)
    topic_ids = config["generated_debates"]["topic_ids"]
    PIPELINE_DIR.mkdir(parents=True, exist_ok=True)
    with (PIPELINE_DIR / "pipeline.log").open("a", encoding="utf-8") as log:
        log.write(f"\nPipeline resume {datetime.now(timezone.utc).isoformat()}\n")
        log.flush()

        run(
            [
                sys.executable,
                "run_real_world_forced_choice_batch.py",
                "--config",
                str(CONFIG),
                "--output-dir",
                str(REAL_RESULTS),
            ],
            log,
        )
        run(
            [
                sys.executable,
                "run_poliprop_ideology_annotation_batch.py",
                "--config",
                str(CONFIG),
                "--output-dir",
                str(ANNOTATIONS),
            ],
            log,
        )
        run(
            [
                sys.executable,
                "analyze_poliprop_ideology_annotations.py",
                "--input-dir",
                str(ANNOTATIONS),
            ],
            log,
        )
        run(
            [
                sys.executable,
                "analyze_real_world_forced_choice.py",
                "--results-dir",
                str(REAL_RESULTS),
                "--ideology",
                str(ANNOTATIONS / "ideology_consensus.csv"),
            ],
            log,
        )

        raw_source = GENERATED / "RawDebates_modelAB_source.csv"
        raw_final = GENERATED / "RawDebates.csv"
        run(
            [
                sys.executable,
                "run_full_rawdebates_batch.py",
                "--source",
                str(raw_source),
                "--final",
                str(raw_final),
                "--transcript-dir",
                str(GENERATED / "transcripts"),
                "--topics-file",
                config["generated_debates"]["topics_file"],
                "--topics",
                *topic_ids,
                "--models",
                models,
                "--target-rows",
                str(config["generated_debates"]["expected_debates"]),
                "--rounds",
                str(config["generated_debates"]["messages_per_debate"]),
                "--max-tokens",
                str(config["generated_debates"]["max_tokens_per_message"]),
            ],
            log,
        )
        run(
            [
                sys.executable,
                "run_generated_forced_choice_batch.py",
                "--config",
                str(CONFIG),
                "--raw",
                str(raw_final),
                "--transcript-dir",
                str(GENERATED / "transcripts"),
                "--output-dir",
                str(GENERATED / "judgements"),
            ],
            log,
        )
        run(
            [
                sys.executable,
                "analyze_six_model_ideology.py",
                "--raw",
                str(raw_final),
                "--judgements",
                str(GENERATED / "judgements"),
                "--config",
                str(CONFIG),
            ],
            log,
        )

        log.write("\nAll primary extension stages completed.\n")
        log.flush()


if __name__ == "__main__":
    main()
