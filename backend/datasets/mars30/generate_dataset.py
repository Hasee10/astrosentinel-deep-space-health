#!/usr/bin/env python3
"""ASTROSENTINEL synthetic Mars-transit dataset: 300 astronauts x 30 days.

SYNTHETIC DATA. Not clinically validated. Every number below is either taken from the
project's approved parameter registry / parameter sheet, or is a labelled
simulation assumption (marked ASSUMPTION). Nothing here is patient data.

Reproduce the delivered files exactly:
    python generate_dataset.py --out .          (seed 2026, 300 astronauts, 30 days)

Design (what each block implements)
-----------------------------------
SANS / ONSD (optic nerve sheath diameter)
  * Personal baseline ~ Normal(5.35, 0.25) mm, clipped to [4.8, 5.9]   [approved: onsd_baseline_sd_values]
  * Daily within-person noise ~ Normal(0, 0.20) mm                       [approved: onsd_baseline_sd_values]
  * Susceptibility: High 25% / Low 75%                                   [approved: sans_prior_mapping]
  * Event probability: High 70% / Low 30% (about 40% overall)            [approved: sans_prior_mapping]
  * Onset day ~ uniform integer 5..20                                    [ASSUMPTION]
  * After onset: ONSD += 0.04 mm x (day - onset), linear, no cap         [ASSUMPTION, from an external unverified CSV]
  * Scan failure injection on ONSD days: 10% of scans; half are off-axis
    (value kept, +0.4 mm bias, quality "degraded"), half are air-under-
    dressing (no value, quality "failed")                                [approved: onsd_scan_failure_rate]

Venous stasis / jugular vein
  * Event probability 6/11 (about 55%), drawn independently of SANS      [parameter sheet: Marshall-Goebel "6 of 11"]
  * Onset day ~ uniform integer 5..20                                    [ASSUMPTION]
  * Area: 12 mm^2 baseline; after onset ramps linearly to 34 mm^2 over
    5 days, then holds                                                   [ASSUMPTION built on Lee 2020 area values 12 / 34 mm^2]
  * Flow class: antegrade before onset; stagnant on days 0-2 after onset;
    retrograde from day 3 after onset                                    [ASSUMPTION]
  * Measurement noise on area: 10% of the true value (multiplicative)    [ASSUMPTION]
  * No jugular scan failures are simulated                               [no approved rate exists]

Scan schedule (data contract = ONE scan per astronaut-day)
  * Jugular scan on days 4, 11, 18, 25; ONSD scan on every other day     [ASSUMPTION: avoids the fixed-schedule days 1,8,15,22,29]

Latent (noise-free) truth is also written, as label_* columns, for denoising /
state-estimation tasks. label_* columns must never be used as model inputs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

SYNTHETIC_LABEL = "SYNTHETIC - NOT CLINICALLY VALIDATED"
FLOW_CLASSES = ["antegrade", "stagnant", "retrograde"]


def build(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(args.seed)
    jug_days = set(args.jugular_days)
    n, n_days = args.n_astronauts, args.days

    astro_rows: list[dict] = []
    day_rows: list[dict] = []

    for i in range(n):
        aid = f"A{i + 1:03d}"

        # ---- SANS ground truth -------------------------------------------------
        high = rng.random() < 0.25
        p_sans = 0.70 if high else 0.30
        has_sans = bool(rng.random() < p_sans)
        sans_onset = int(rng.integers(args.onset_min, args.onset_max + 1)) if has_sans else None
        baseline = float(np.clip(rng.normal(5.35, 0.25), 4.8, 5.9))

        # ---- venous ground truth (independent of SANS) -------------------------
        has_ven = bool(rng.random() < args.venous_event_rate)
        ven_onset = int(rng.integers(args.onset_min, args.onset_max + 1)) if has_ven else None

        scenario = (
            "both" if (has_sans and has_ven)
            else "sans_only" if has_sans
            else "venous_only" if has_ven
            else "healthy"
        )
        astro_rows.append(
            dict(
                astronaut_id=aid,
                scenario=scenario,
                susceptibility_class="high" if high else "low",
                onsd_baseline_mm=round(baseline, 4),
                has_sans_event=int(has_sans),
                sans_onset_day=sans_onset,
                has_venous_event=int(has_ven),
                venous_onset_day=ven_onset,
            )
        )

        for day in range(1, n_days + 1):
            # latent SANS state
            sans_active = has_sans and day >= sans_onset
            sans_dsince = (day - sans_onset) if sans_active else None
            true_onsd = baseline + (args.sans_slope_mm_per_day * (day - sans_onset) if sans_active else 0.0)

            # latent venous state
            ven_active = has_ven and day >= ven_onset
            ven_dsince = (day - ven_onset) if ven_active else None
            if ven_active:
                ramp = min(1.0, (day - ven_onset) / args.area_ramp_days)
                true_area = args.area_baseline + (args.area_peak - args.area_baseline) * ramp
                true_flow = "stagnant" if (day - ven_onset) <= 2 else "retrograde"
            else:
                true_area, true_flow = args.area_baseline, "antegrade"

            row = dict(
                astronaut_id=aid,
                day=day,
                scan_type="jugular" if day in jug_days else "onsd",
                onsd_mm=np.nan,
                onsd_on_axis=np.nan,
                scan_quality_status="",
                jugular_area_mm2=np.nan,
                jugular_flow_class="",
                label_sans_event_active=int(sans_active),
                label_sans_days_since_onset=sans_dsince,
                label_venous_event_active=int(ven_active),
                label_venous_days_since_onset=ven_dsince,
                label_true_onsd_mm=round(true_onsd, 4),
                label_true_jugular_area_mm2=round(true_area, 4),
                label_true_flow_class=true_flow,
            )

            if day in jug_days:
                area = true_area * (1.0 + rng.normal(0.0, args.area_noise_frac))
                flow = true_flow
                if args.flow_misread_rate > 0 and rng.random() < args.flow_misread_rate:
                    flow = str(rng.choice([c for c in FLOW_CLASSES if c != true_flow]))
                row.update(jugular_area_mm2=round(float(max(area, 0.0)), 3), jugular_flow_class=flow,
                           scan_quality_status="ok")
            else:
                reading = true_onsd + rng.normal(0.0, args.onsd_noise_sd)
                if rng.random() < args.onsd_failure_rate:
                    if rng.random() < 0.5:  # off-axis: value kept, positive bias, degraded
                        row.update(onsd_mm=round(float(reading + args.off_axis_bias_mm), 3), onsd_on_axis=0,
                                   scan_quality_status="degraded")
                    else:  # air under dressing: no usable value
                        row.update(scan_quality_status="failed")
                else:
                    row.update(onsd_mm=round(float(reading), 3), onsd_on_axis=1, scan_quality_status="ok")
            day_rows.append(row)

    astro = pd.DataFrame(astro_rows)

    # ---- split by ASTRONAUT, stratified by scenario (70/15/15) -----------------
    split = pd.Series("train", index=astro.index)
    for _, grp in astro.groupby("scenario"):
        idx = rng.permutation(grp.index.to_numpy())
        n_test = int(round(0.15 * len(idx)))
        n_val = int(round(0.15 * len(idx)))
        split.loc[idx[:n_test]] = "test"
        split.loc[idx[n_test:n_test + n_val]] = "val"
    astro.insert(1, "split", split)

    days = pd.DataFrame(day_rows)
    for col in ["onsd_on_axis", "label_sans_days_since_onset", "label_venous_days_since_onset"]:
        days[col] = days[col].astype("Int64")  # integers with blanks, not 1.0 / 0.0
    for col in ["sans_onset_day", "venous_onset_day"]:
        astro[col] = astro[col].astype("Int64")
    days.insert(2, "split", days["astronaut_id"].map(astro.set_index("astronaut_id")["split"]))
    return days, astro


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", type=Path, default=Path("."))
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--n-astronauts", type=int, default=300)
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--onset-min", type=int, default=5)
    p.add_argument("--onset-max", type=int, default=20)
    p.add_argument("--sans-slope-mm-per-day", type=float, default=0.04)
    p.add_argument("--onsd-noise-sd", type=float, default=0.20)
    p.add_argument("--onsd-failure-rate", type=float, default=0.10)
    p.add_argument("--off-axis-bias-mm", type=float, default=0.4)
    p.add_argument("--venous-event-rate", type=float, default=6 / 11)
    p.add_argument("--area-baseline", type=float, default=12.0)
    p.add_argument("--area-peak", type=float, default=34.0)
    p.add_argument("--area-ramp-days", type=float, default=5.0)
    p.add_argument("--area-noise-frac", type=float, default=0.10)
    p.add_argument("--jugular-days", type=int, nargs="+", default=[4, 11, 18, 25])
    p.add_argument("--flow-misread-rate", type=float, default=0.0,
                   help="Optional harder variant: chance a jugular flow class is read as a wrong class. Delivered file uses 0.")
    args = p.parse_args()

    days, astro = build(args)
    args.out.mkdir(parents=True, exist_ok=True)
    days.to_csv(args.out / "astronaut_days.csv", index=False)
    astro.to_csv(args.out / "astronauts.csv", index=False)
    meta = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items() if k != "out"}
    meta["label"] = SYNTHETIC_LABEL
    (args.out / "generation_params.json").write_text(json.dumps(meta, indent=2))
    print(f"wrote {len(days)} astronaut-days, {len(astro)} astronauts -> {args.out}")


if __name__ == "__main__":
    main()
