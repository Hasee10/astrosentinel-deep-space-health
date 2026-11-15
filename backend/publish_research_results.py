#!/usr/bin/env python
"""Builds the public, aggregate-only research results file the frontend's
Research -> Results panel reads (final-submission directive, 2026-11-15,
Priority 1). Combines three already-computed, already-tested outputs - never
recomputes anything itself, so there is exactly one source of truth for each
number:

  - backend/datasets/mars30/baseline_results.json (ML baseline, reproduced by
    the dataset's own baseline_example.py)
  - handoff/submission/mars30_schedule_comparison.json (fixed-vs-adaptive SANS
    scheduling comparison, backend/evaluation/mars30_schedule_comparison.py)
  - backend/outputs/mars30_pipeline/scoring_summary.json (SANS/venous tier
    distribution over the full published cohort)

Contains only cohort-level aggregates - no per-astronaut scenario, onset, or
susceptibility label, same public/evaluation-only boundary
publish_frontend_demo_data.py already enforces for the pipeline files.

Usage:
    python publish_research_results.py
"""
from __future__ import annotations

import json
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent


def main() -> int:
    baseline = json.loads((BACKEND_DIR / "datasets" / "mars30" / "baseline_results.json").read_text(encoding="utf-8"))
    schedule = json.loads((REPO_ROOT / "handoff" / "submission" / "mars30_schedule_comparison.json").read_text(encoding="utf-8"))
    scoring_summary = json.loads((BACKEND_DIR / "outputs" / "mars30_pipeline" / "scoring_summary.json").read_text(encoding="utf-8"))

    out = {
        "label": "Mars30 collaborator dataset - final-submission synthetic study",
        "validated_for_experiment": False,
        "disclaimer": "SYNTHETIC. Not clinically validated. Every figure below is a computed result of this repository's own code against a synthetic dataset.",
        "correction_notice": (
            "An earlier version of this study tested the latest ONSD against an absolute 5.0mm cutoff. "
            "That was a misreading of the collaborator's specification (personal-baseline-relative, "
            "+0.4mm) and produced an unusable ~96-99% false-escalation rate. Corrected 2026-11-15; the "
            "superseded run is preserved at handoff/submission/AUDIT_superseded_absolute_cutoff_run/."
        ),
        "dataset": {
            "astronauts": 300,
            "mission_days": 30,
            "records": 9000,
            "split": {"train_astronauts": 210, "val_astronauts": 45, "test_astronauts": 45},
            "split_unit": "astronaut (no astronaut appears in two splits)",
            "scenario_mix": {"healthy": 75, "sans_only": 57, "venous_only": 101, "both": 67},
            "source": "backend/datasets/mars30 (collaborator-provided, seed 2026)",
            "validated": "validate_dataset.py - ALL CHECKS PASSED",
        },
        "ml_baseline": {
            "description": "Causal-feature models reproduced from the dataset's own baseline_example.py (test split, 45 astronauts). Not the deployed monitoring model - a reference bar.",
            "sans": baseline["sans"],
            "venous": baseline["venous"],
        },
        "sans_bayesian_rule": {
            "description": "Collaborator's corrected 2026-11-15 specification: latest quality-OK ONSD reading tested against this astronaut's own causally-estimated personal baseline (median of the first 3 quality-OK readings seen so far) - positive if >=0.4mm above baseline, applying LR+ 6.93; else LR- 0.04. Single latest reading only, never multiplied across days.",
            "lr_positive": 6.93,
            "lr_negative": 0.04,
            "delta_threshold_mm": 0.4,
            "starting_prior_pct": 5,
            "probability_label": "Simulation placeholder - unvalidated",
            "full_cohort_tier_distribution": {
                "sans": scoring_summary["sans_tier_distribution"],
                "venous": scoring_summary["venous_tier_distribution"],
            },
            "authorization_scope": (
                "User-relayed approval for this synthetic submission experiment only - not independent "
                "written research-lead sign-off, peer review, or clinical validation. The LR values are a "
                "real cited figure (Koziarz et al. 2019) for an absolute-cutoff ICU/ICP test; reusing them "
                "for this personal-baseline-delta SANS test is an additional reuse choice, not something "
                "that study itself measured."
            ),
        },
        "fixed_vs_adaptive": {
            "description": schedule["note"],
            "trigger_accuracy_used": schedule["trigger_accuracy_used"],
            "trigger_accuracy_approved_sweep": [0.5, 0.6, 0.7, 0.8, 0.9],
            "n_event_astronauts": schedule["n_event_astronauts"],
            "n_nonevent_astronauts": schedule["n_nonevent_astronauts"],
            "by_interval": schedule["by_interval"],
        },
        "completed_synthetic_experiments": [
            "ML baseline (SANS + venous) reproduced on the real Mars30 train/val/test split",
            "SANS Bayesian probability rule, corrected to the personal-baseline-delta specification",
            "Fixed-vs-adaptive SANS scanning comparison at 3/7/14-day intervals",
        ],
        "scientific_assumptions_and_limitations": [
            "Every number on this page is synthetic and not clinically validated.",
            "sans_probability_model / onsd_cutoff_risk_mapping are user-relayed approvals for this submission only - see authorization_scope above.",
            "The 5% starting Bayesian prior has no literature source; it mirrors the venous model's identical placeholder for architectural consistency.",
            "The personal baseline is estimated from only the first 3 quality-OK ONSD readings seen so far per astronaut - a documented protocol choice, not a validated clinical baseline-estimation method.",
            "Venous is excluded from the fixed-vs-adaptive scheduling comparison per directive - its jugular scan days (4/11/18/25) are fixed by the dataset's own design, not a policy variable here.",
            "Trigger-firing behavior uses the approved HRV-proxy sensitivity model at accuracy=0.7 (middle of the approved 0.5-0.9 sweep) - not a measured trigger accuracy.",
        ],
        "genuinely_blocked_future_work": [
            "A venous fixed-vs-adaptive scheduling comparison - the jugular scan schedule is fixed by the dataset design, not a policy this codebase can vary without a different dataset or a new generation model.",
            "Any Urgent-tier demonstration from this dataset - Mars30 has no symptom/red-flag field, and this codebase's Urgent tier is rule-based on red-flag symptoms only, never probability-based.",
            "Independent written research-lead or clinical sign-off on the SANS Bayesian rule - see authorization_scope.",
        ],
    }

    out_path = REPO_ROOT / "frontend" / "public" / "data" / "research" / "results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
