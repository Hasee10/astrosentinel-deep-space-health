"""Fixed-vs-adaptive SANS scanning comparison on the Mars30 collaborator dataset
(final-submission directive, 2026-11-15, Priority 2).

Reuses, rather than reinvents, two already-approved pieces of this codebase:
  - evaluation/policies.py's FixedSchedulePolicy and AdaptiveSchedulePolicy
    ("fixed backstop PLUS triggered scans", exactly the collaborator's spec).
  - evaluation/trigger_model.py's approved windowed-sensitivity trigger-firing
    formula and hrv_trigger_assumed_accuracy's approved sweep/false-fire rate,
    wired to SANS onset only (never venous - venous is kept out of this
    comparison per the directive, and the trigger model was never approved for
    it anyway).
  - monitoring/engine.py's approved SANS Bayesian rule (onsd_cutoff_risk_mapping:
    cutoff 5.0mm, LR+ 6.93, LR- 0.04) and decision_tier_thresholds' approved
    Consult cutoff (40%) as the escalation/alert point.

What is new here is only the glue: Mars30's real per-astronaut-day ONSD values
replace the synthetic generator as the source of evidence, and a jugular-only
day (4, 11, 18, 25 in this dataset) is handled explicitly - no ONSD measurement
exists on those days regardless of what the SANS schedule calls for (one scan
per astronaut-day, by the dataset's own design), so a scan "due" on such a day
is simply unavailable that day, not substituted or skipped silently.

Detection delay, missed events and false escalations are measured against the
posterior computed from the latest quality-OK ONSD reading actually taken under
each policy up to and including that day - never a reading the policy did not
yet take, and never multiple readings multiplied together (same discipline as
monitoring/engine.py).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from evaluation.policies import AdaptiveSchedulePolicy, FixedSchedulePolicy
from evaluation.trigger_model import per_day_firing_probability

CUTOFF_MM = 5.0
LR_POSITIVE = 6.93
LR_NEGATIVE = 0.04
STARTING_PRIOR_PCT = 5  # mirrors registry onsd_cutoff_risk_mapping / jugular_flow_risk_mapping placeholder
ALERT_MIN_PCT = 15  # registry decision_tier_thresholds.repeat_min_pct. NOT consult_min_pct (40): with a
# single latest-reading LR+6.93 from a 5% prior, the posterior caps at ~26.7% and can never reach 40%
# (the same structural ceiling test_recovery_acceptance.py documents for the venous LR=10 case) - using
# 40% here would report zero detections regardless of policy, which is not an honest comparison.
JUGULAR_ONLY_DAYS = {4, 11, 18, 25}  # this dataset's fixed venous acquisition days (see astronaut_days.csv)
MISSION_DAYS = 30

TRIGGER_WINDOW_DAYS = 5  # hrv_trigger_assumed_accuracy.post_onset_window_days
BASE_FALSE_FIRE_PROBABILITY = 0.05  # hrv_trigger_assumed_accuracy.base_false_fire_probability_per_day


def sans_posterior_pct(onsd_mm: float) -> float:
    lr = LR_POSITIVE if onsd_mm >= CUTOFF_MM else LR_NEGATIVE
    prior = STARTING_PRIOR_PCT / 100.0
    prior_odds = prior / (1 - prior)
    posterior_odds = prior_odds * lr
    return 100.0 * posterior_odds / (1 + posterior_odds)


@dataclass
class PolicyRunResult:
    policy_name: str
    total_scans: int
    detected: int
    missed: int
    median_delay_days: float | None
    mean_delay_days: float | None
    false_escalation_rate: float
    n_event_astronauts: int
    n_nonevent_astronauts: int
    per_astronaut_alert_day: dict[str, int | None]


def _trigger_fires(rng_seed: str, day: int, onset_day: int | None, accuracy: float) -> bool:
    import random

    h = per_day_firing_probability(accuracy, TRIGGER_WINDOW_DAYS)
    in_window = onset_day is not None and onset_day <= day < onset_day + TRIGGER_WINDOW_DAYS
    probability = h if in_window else BASE_FALSE_FIRE_PROBABILITY
    rng = random.Random(f"{rng_seed}:{day}")
    return rng.random() < probability


def _run_policy(
    days_df: pd.DataFrame,
    astro_df: pd.DataFrame,
    policy_name: str,
    is_scan_due,
    trigger_accuracy: float | None,
    seed: int,
) -> PolicyRunResult:
    onsd_by_astro_day = {
        (r.astronaut_id, r.day): r.onsd_mm
        for r in days_df.itertuples()
        if r.scan_type == "onsd"
    }
    quality_by_astro_day = {
        (r.astronaut_id, r.day): r.scan_quality_status
        for r in days_df.itertuples()
        if r.scan_type == "onsd"
    }

    total_scans = 0
    delays: list[int] = []
    missed = 0
    false_escalations = 0
    per_astronaut_alert_day: dict[str, int | None] = {}
    n_event, n_nonevent = 0, 0

    for astro in astro_df.itertuples():
        aid = astro.astronaut_id
        onset = astro.sans_onset_day if astro.has_sans_event else None
        is_event = bool(astro.has_sans_event)
        n_event += int(is_event)
        n_nonevent += int(not is_event)

        last_good_onsd: float | None = None
        alert_day: int | None = None
        for day in range(1, MISSION_DAYS + 1):
            if day in JUGULAR_ONLY_DAYS:
                continue  # no ONSD measurement possible this day, regardless of schedule
            if trigger_accuracy is None:
                due = is_scan_due(day)
            else:
                fired = _trigger_fires(f"{seed}:{aid}", day, int(onset) if onset is not None else None, trigger_accuracy)
                due = is_scan_due(day, fired)
            if not due:
                continue

            total_scans += 1
            key = (aid, day)
            quality = quality_by_astro_day.get(key)
            value = onsd_by_astro_day.get(key)
            if quality == "ok" and value is not None and value == value:  # value==value excludes NaN
                last_good_onsd = value

            if last_good_onsd is None or alert_day is not None:
                continue
            posterior = sans_posterior_pct(last_good_onsd)
            if posterior >= ALERT_MIN_PCT:
                alert_day = day

        per_astronaut_alert_day[aid] = alert_day
        if is_event:
            if alert_day is None or alert_day < onset:
                missed += 1
            else:
                delays.append(alert_day - int(onset))
        else:
            if alert_day is not None:
                false_escalations += 1

    return PolicyRunResult(
        policy_name=policy_name,
        total_scans=total_scans,
        detected=n_event - missed,
        missed=missed,
        median_delay_days=float(pd.Series(delays).median()) if delays else None,
        mean_delay_days=float(pd.Series(delays).mean()) if delays else None,
        false_escalation_rate=round(false_escalations / n_nonevent, 4) if n_nonevent else float("nan"),
        n_event_astronauts=n_event,
        n_nonevent_astronauts=n_nonevent,
        per_astronaut_alert_day=per_astronaut_alert_day,
    )


def run_comparison(
    dataset_dir: Path, trigger_accuracy: float = 0.7, seed: int = 2026
) -> dict:
    """trigger_accuracy defaults to 0.7, the middle of hrv_trigger_assumed_accuracy's
    approved sweep [0.5, 0.6, 0.7, 0.8, 0.9] - callers may pass any swept value."""
    days_df = pd.read_csv(dataset_dir / "astronaut_days.csv")
    astro_df = pd.read_csv(dataset_dir / "astronauts.csv")

    results: dict[str, PolicyRunResult] = {}
    for interval in (3, 7, 14):
        fixed = FixedSchedulePolicy(interval_days=interval)
        results[f"fixed_{interval}d"] = _run_policy(
            days_df, astro_df, f"fixed_{interval}d", fixed.is_scan_due, None, seed
        )
        adaptive = AdaptiveSchedulePolicy(interval_days=interval)
        results[f"adaptive_{interval}d"] = _run_policy(
            days_df, astro_df, f"adaptive_{interval}d", adaptive.is_scan_due, trigger_accuracy, seed
        )

    summary = {}
    for interval in (3, 7, 14):
        f, a = results[f"fixed_{interval}d"], results[f"adaptive_{interval}d"]
        extra_scans = a.total_scans - f.total_scans
        common_detected = [
            aid for aid in f.per_astronaut_alert_day
            if f.per_astronaut_alert_day[aid] is not None and a.per_astronaut_alert_day[aid] is not None
        ]
        days_saved_total = sum(
            f.per_astronaut_alert_day[aid] - a.per_astronaut_alert_day[aid] for aid in common_detected
        )
        # astronauts the adaptive policy detects but fixed misses: count full fixed-missed delay as "saved"
        adaptive_only = [
            aid for aid in a.per_astronaut_alert_day
            if a.per_astronaut_alert_day[aid] is not None and f.per_astronaut_alert_day[aid] is None
        ]
        days_saved_total += sum((MISSION_DAYS + 1 - a.per_astronaut_alert_day[aid]) for aid in adaptive_only)
        summary[f"{interval}d"] = {
            "fixed": {
                "total_scans": f.total_scans, "detected": f.detected, "missed": f.missed,
                "median_delay_days": f.median_delay_days, "mean_delay_days": f.mean_delay_days,
                "false_escalation_rate": f.false_escalation_rate,
            },
            "adaptive": {
                "total_scans": a.total_scans, "detected": a.detected, "missed": a.missed,
                "median_delay_days": a.median_delay_days, "mean_delay_days": a.mean_delay_days,
                "false_escalation_rate": a.false_escalation_rate,
            },
            "extra_scans_used_by_adaptive": extra_scans,
            "total_days_saved_by_adaptive": days_saved_total,
            "days_saved_per_additional_scan": round(days_saved_total / extra_scans, 3) if extra_scans else None,
        }
    return {
        "trigger_accuracy_used": trigger_accuracy,
        "n_event_astronauts": results["fixed_7d"].n_event_astronauts,
        "n_nonevent_astronauts": results["fixed_7d"].n_nonevent_astronauts,
        "note": "SANS only, per directive. Alert = posterior >= 15% (decision_tier_thresholds.repeat_min_pct) from the latest quality-OK ONSD reading actually taken under each policy - the single-latest-reading LR+6.93 model from a 5% prior cannot reach the 40% Consult threshold (posterior caps at ~26.7%), the same structural ceiling test_recovery_acceptance.py documents for the venous LR=10 case. Jugular-only days (4,11,18,25) never carry an ONSD reading.",
        "by_interval": summary,
    }


def main() -> None:
    dataset_dir = Path(__file__).resolve().parents[1] / "datasets" / "mars30"
    out = run_comparison(dataset_dir)
    out_path = Path(__file__).resolve().parents[2] / "handoff" / "submission" / "mars30_schedule_comparison.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    print(f"\nWritten to {out_path}")


if __name__ == "__main__":
    main()
