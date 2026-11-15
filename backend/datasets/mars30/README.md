# ASTROSENTINEL synthetic dataset: 300 astronauts × 30 days (Mars transit)

**SYNTHETIC. Not clinically validated.** Every row is simulated. Do not present any result from this
data as clinical evidence. Anything a model learns here is "how well it recovers our generator's rules."

## Files

| File | What it is |
|---|---|
| `astronaut_days.csv` | 9,000 rows (300 astronauts × 30 days). Observed measurements + `label_*` columns. **This is the training table.** |
| `astronauts.csv` | One row per astronaut: scenario, split, hidden onset days, susceptibility, baseline. **Ground truth. Never a model input.** |
| `generate_dataset.py` | Reproduces the files exactly (`python generate_dataset.py --out .`, seed 2026). Every parameter is a CLI flag. |
| `baseline_example.py` | Reference train/val/test protocol and baseline models. Run it first. |
| `validate_dataset.py` | Re-checks the CSVs against the design (`python validate_dataset.py .`). All checks pass. |
| `generation_params.json` | Exact parameters used. |
| `baseline_results.json` | Output of `baseline_example.py`. |

## Columns of `astronaut_days.csv`

**Inputs (what a monitoring model may see):**

| Column | Meaning |
|---|---|
| `astronaut_id`, `day` | A001–A300, day 1–30 |
| `split` | `train` (210 astronauts) / `val` (45) / `test` (45). Split by astronaut, stratified by scenario. |
| `scan_type` | `onsd` or `jugular`. **One scan per astronaut-day.** Jugular on days 4, 11, 18, 25; ONSD on all other days. |
| `onsd_mm` | Optic nerve sheath diameter. Blank on jugular days and on failed scans. |
| `onsd_on_axis` | 1 = on-axis, 0 = off-axis. Blank on jugular days and on failed scans. |
| `scan_quality_status` | `ok`, `degraded` (off-axis: value kept but biased +0.4 mm), or `failed` (no value). Jugular scans are always `ok`. |
| `jugular_area_mm2` | Jugular cross-sectional area. Blank on ONSD days. |
| `jugular_flow_class` | `antegrade`, `stagnant` or `retrograde`. Blank on ONSD days. |

**Labels (targets or evaluation only, never inputs):**

| Column | Meaning |
|---|---|
| `label_sans_event_active` | 1 from the SANS onset day onward |
| `label_sans_days_since_onset` | 0, 1, 2, … after onset; blank before onset or if no event |
| `label_venous_event_active` | 1 from the venous onset day onward |
| `label_venous_days_since_onset` | Same idea for venous |
| `label_true_onsd_mm` | Noise-free ONSD every day (for denoising / state estimation) |
| `label_true_jugular_area_mm2`, `label_true_flow_class` | Noise-free jugular state every day, including days with no jugular scan |

## How the data was generated

Each item is tagged **approved** (in the project registry or sheet) or **assumption** (simulation design choice, label it as such).

**SANS / ONSD**
- Personal baseline ~ Normal(5.35, 0.25) mm, clipped to 4.8–5.9. *approved*
- Daily within-person noise SD 0.20 mm. *approved*
- Susceptibility 25% high / 75% low. Event probability 70% high / 30% low (about 40% overall). *approved*
- Onset day uniform 5–20. *assumption*
- After onset ONSD rises **+0.04 mm per day, linear, no cap**. *assumption, from an external unverified CSV, not literature*
- Scan failures: 10% of ONSD scans; half off-axis (value +0.4 mm, `degraded`), half air-under-dressing (`failed`, no value). *approved*

**Venous stasis / jugular**
- 6 of 11 astronauts (about 55%) get an event, independent of SANS. *parameter sheet (Marshall-Goebel "6 of 11")*. It counts stagnant or retrograde flow, so it is a venous stasis event, not thrombosis.
- Onset uniform 5–20. *assumption*
- Area: 12 mm² baseline, ramping linearly to 34 mm² over the 5 days after onset, then holding. *assumption using the 12 and 34 mm² values of Lee 2020*
- Flow class: antegrade before onset, stagnant on days 0–2 after onset, retrograde from day 3. *assumption*
- Area measurement noise 10% of the value. *assumption*
- No jugular scan failures are simulated. *no approved rate exists*

Scenario mix in this file: healthy 75, SANS only 57, venous only 101, both 67. Realised event rates: SANS 41.3%, venous 56.0%.

## What we want from the model

The model outputs **a probability per outcome per day**, SANS and venous **separately** (never a combined score), which maps to tiers at **15% (Repeat), 40% (Consult), 80% (Urgent)**.

1. **SANS state detector.** Predict `label_sans_event_active` each day from ONSD history. Use personal-baseline features (change from the astronaut's own early readings), not an absolute 5.0 mm cutoff. About 90% of healthy astronauts sit above 5.0 mm at baseline.
2. **Venous state detector.** Predict `label_venous_event_active` from the jugular history (latest flow class, area, days since last scan).
3. **Calibration.** The output must behave like a probability. Report a reliability curve and Brier score on `val`/`test`.
4. **Detection delay.** For each event astronaut, report days from onset to first alert, at a threshold set so that no more than 5% of event-free astronauts ever alert. Report the detected count and the missed count.
5. **Robustness (optional).** Regenerate with `--onsd-noise-sd 0.3`, `--sans-slope-mm-per-day 0.02` and `--flow-misread-rate 0.1`. Show how the metrics move. These stress-test the assumptions.

## Rules

- **Causal features only.** Row (astronaut, day) may use only observations from days ≤ that day.
- **No leakage.** Never use `label_*`, `astronauts.csv`, `scenario` or `susceptibility_class` as inputs.
- **Split by astronaut** using the `split` column. Choose thresholds on `val`, report on `test`. The test set is only 45 astronauts, so numbers are noisy. Prefer cross-validation grouped by astronaut for any claim.
- **Baseline window.** Days 1–4 are event-free by construction, since onsets start at day 5. Real use would need a pre-flight baseline, so say this in any write-up.
- **Quality handling.** Degraded scans are biased +0.4 mm and failed scans are blank. A missing value is "unresolved", never zero.
- **Every output labelled** "synthetic simulation, not clinically validated".

## Baseline to beat (`python baseline_example.py`, test astronauts)

| Task | Model | AUROC | Event-free astronauts alerted | Events detected | Median delay (days) |
|---|---|---|---|---|---|
| SANS | hand rule (latest ONSD − baseline) | 0.809 | 7.7% | 15/19 | 13 |
| SANS | logistic | 0.814 | 3.8% | 16/19 | 13 |
| SANS | gradient boosting | 0.861 | 3.8% | 16/19 | 11 |
| Venous | hand rule (approved LRs, latest scan) | 0.898 | 0% | 25/25 | 6 |
| Venous | logistic | 0.931 | 5.0% | 25/25 | 5 |
| Venous | gradient boosting | 0.928 | 0% | 25/25 | 6 |

Two things these numbers say:
- **SANS is hard.** The ONSD slope is 0.04 mm/day against 0.20 mm of daily noise, so a typical event takes 11–13 days to flag. A better model, or more scans in the right place, helps here.
- **Venous detection is limited by the schedule, not the model.** Jugular scans happen on only 4 days. The median wait from onset to the next scan is 4 days, and the maximum is 6. No model can detect before the next scan, so the lever is scan timing, not model quality.

## Limits

- Everything is synthetic. The ONSD slope, onset days, area ramp, flow-class timing and noise are labelled assumptions. If the real signals differ, trained models will not transfer.
- The flow class is noise-free in the delivered file, so venous classification is easy. Use `--flow-misread-rate` for a harder version.
- HRV and pulse-transit weak signals are not included.
- Venous scheduling studies need more jugular scans. Regenerate with different `--jugular-days`, remembering there is one scan per day, so ONSD disappears on those days.
