#!/usr/bin/env python
"""Converts the Mars30 collaborator dataset into this project's existing
AstronautDayObservation/AssessmentResult pipeline, then publishes it to the
frontend exactly the way a synthetic generate_crew.py run already does.

Final-submission directive (2026-11-15), Priority 3: loads all 300 Mars30
profiles through the SAME contract, scoring engine (monitoring/engine.py, now
with the approved SANS Bayesian model), and public-data sanitizer
(publish_frontend_demo_data.py) the project already built and tested for the
synthetic generator - no new schema, no new frontend code, no separate
"research view" data path. Ground truth (astronauts.csv: scenario, onset days,
susceptibility) is read ONLY to write a separate evaluation-only file; it is
never passed into assess_history() or any scan/quality field, the same
boundary GroundTruthRecord already enforces for the synthetic generator.

Usage:
    python mars30_to_pipeline.py --output-dir outputs/mars30_pipeline
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from contracts.models import (
    AstronautDayObservation,
    MeasurementQuality,
    ObservationMetadata,
    QualityStatus,
    ScanMeasurement,
    ScanType,
)
from registry.loader import load_all

RUN_ID = "mars30-collaborator-2026"
SYNTHETIC_LABEL = "SYNTHETIC - NOT CLINICALLY VALIDATED (Mars30 collaborator dataset, generate_dataset.py seed 2026)"
DATASET_DIR = Path(__file__).resolve().parent / "datasets" / "mars30"

_QUALITY_MAP = {
    "ok": QualityStatus.OK,
    "degraded": QualityStatus.DEGRADED,
    "failed": QualityStatus.FAILED,
}


def _scan_for_row(row) -> ScanMeasurement | None:
    if row.scan_type == "onsd":
        onsd_mm = None if pd.isna(row.onsd_mm) else float(row.onsd_mm)
        on_axis = None if pd.isna(row.onsd_on_axis) else bool(row.onsd_on_axis)
        return ScanMeasurement(
            type=ScanType.ONSD,
            onsd_mm=onsd_mm,
            on_axis=on_axis,
            quality=MeasurementQuality(status=_QUALITY_MAP[row.scan_quality_status]),
        )
    if row.scan_type == "jugular":
        return ScanMeasurement(
            type=ScanType.JUGULAR,
            jugular_area_mm2=None if pd.isna(row.jugular_area_mm2) else float(row.jugular_area_mm2),
            jugular_flow_class=row.jugular_flow_class,
            quality=MeasurementQuality(status=_QUALITY_MAP[row.scan_quality_status]),
        )
    raise ValueError(f"unknown scan_type {row.scan_type!r}")


def build_observations(days_df: pd.DataFrame) -> list[AstronautDayObservation]:
    observations = []
    for row in days_df.sort_values(["astronaut_id", "day"]).itertuples():
        observations.append(AstronautDayObservation(
            astronaut_id=row.astronaut_id,
            day=int(row.day),
            scan=_scan_for_row(row),
            metadata=ObservationMetadata(
                synthetic=True,
                synthetic_label=SYNTHETIC_LABEL,
                run_id=RUN_ID,
            ),
        ))
    return observations


def write_ground_truth(astro_df: pd.DataFrame, output_dir: Path) -> Path:
    """Evaluation-only. Never read by assess_history() or publish_frontend_demo_data.py."""
    path = output_dir / "ground_truth.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for row in astro_df.itertuples():
            f.write(json.dumps({
                "astronaut_id": row.astronaut_id,
                "split": row.split,
                "scenario": row.scenario,
                "susceptibility_class": row.susceptibility_class,
                "has_sans_event": bool(row.has_sans_event),
                "sans_onset_day": None if pd.isna(row.sans_onset_day) else int(row.sans_onset_day),
                "has_venous_event": bool(row.has_venous_event),
                "venous_onset_day": None if pd.isna(row.venous_onset_day) else int(row.venous_onset_day),
            }) + "\n")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/mars30_pipeline"))
    args = parser.parse_args()

    days_df = pd.read_csv(DATASET_DIR / "astronaut_days.csv")
    astro_df = pd.read_csv(DATASET_DIR / "astronauts.csv")
    registry = load_all()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    observations = build_observations(days_df)
    obs_path = args.output_dir / "crew_observations.jsonl"
    with obs_path.open("w", encoding="utf-8") as f:
        for obs in observations:
            f.write(obs.model_dump_json() + "\n")

    manifest = {
        "run_id": RUN_ID,
        "created_at": "2026-11-15T00:00:00Z",
        "random_seed": 2026,
        "crew_size": int(astro_df.astronaut_id.nunique()),
        "mission_duration_days": 30,
        "scenario_counts": {},  # never published - stripped again defensively by publish_frontend_demo_data.py
        "parameter_registry_parameter_count": len(registry.parameters),
        "assumption_registry_assumption_count": len(registry.assumptions),
        "active_assumption_ids": sorted(aid for aid, a in registry.assumptions.items() if a.is_active()),
        "physiological_values_generated": True,
        "physiological_generation_blocked_reasons": {},
        "capability_readiness": {},
        "generation_status": "complete",
    }
    (args.output_dir / "simulation_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    gt_path = write_ground_truth(astro_df, args.output_dir)

    from score_crew import score_crew
    score_paths = score_crew(obs_path, args.output_dir)

    print(f"Wrote {len(observations)} observations ({args.output_dir / 'crew_observations.jsonl'})")
    print(f"Wrote ground truth (evaluation-only, never published): {gt_path}")
    print(f"Scored: {score_paths['scored']}")
    print(f"Summary: {score_paths['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
