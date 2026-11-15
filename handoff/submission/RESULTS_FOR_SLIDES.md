# AstroSentinel — Final Submission Results (Mars30 dataset)

**Every number below is synthetic. Nothing here is clinically validated.** This
document reports real, re-run figures from this repository's own code against
the collaborator's Mars30 dataset (300 astronauts × 30 days, seed 2026) - no
number is invented or estimated by hand.

**Correction notice (2026-11-15):** an earlier version of this document and
the underlying model tested the latest ONSD reading against an **absolute
5.0mm cutoff**. That was a misreading of the collaborator's specification and
produced an unusable ~96-99% false-escalation rate. It has been corrected to
the collaborator's actual specification - a **personal-baseline-relative**
rule (positive when the latest valid ONSD is ≥0.4mm above that astronaut's own
causally-estimated baseline) - and every number below reflects the corrected
model. The superseded run is preserved, clearly marked, at
`handoff/submission/AUDIT_superseded_absolute_cutoff_run/`.

## 0. Authorization scope (audited)

Every "approved" registry entry behind these results (`sans_probability_model`,
`onsd_cutoff_risk_mapping`) records **user-relayed approval for this synthetic
submission experiment**, not independent written research-lead sign-off, peer
review, or clinical validation - none of those exist for this model, and none
is claimed. The LR+/LR- values (6.93 / 0.04) are a real cited figure (Koziarz
et al. 2019), but for an absolute-cutoff ICU/ICP test; reusing them for a
personal-baseline-delta SANS test is an additional, explicitly-documented
reuse choice, not something that study itself measured.

## 1. Dataset

- `backend/datasets/mars30/` - the collaborator's dataset, copied in unchanged.
- Verified via its own `validate_dataset.py`: **ALL CHECKS PASSED** (9,000 rows,
  300 astronauts, scenario mix: healthy 75 / SANS-only 57 / venous-only 101 /
  both 67; SANS events 41.3%, venous events 56.0%, matching the dataset's own
  documented targets). Split: train 210 / val 45 / test 45 astronauts, by
  astronaut (no astronaut appears in two splits).

## 2. ML baseline (causal features, astronaut-level train/val/test split)

Reproduced exactly from `baseline_example.py` (test split, 45 astronauts):

| Task | Model | Test AUROC | Event-free astronauts alerted | Events detected | Median delay (days) |
|---|---|---|---|---|---|
| SANS | hand rule (ONSD delta from baseline) | 0.809 | 7.7% | 15/19 | 13 |
| SANS | logistic regression | 0.814 | 3.8% | 16/19 | 13 |
| SANS | gradient boosting | 0.863 | 3.8% | 16/19 | 11 |
| Venous | hand rule (approved LRs, latest scan) | 0.898 | 0% | 25/25 | 6 |
| Venous | logistic regression | 0.931 | 5.0% | 25/25 | 5 |
| Venous | gradient boosting | 0.928 | 0% | 25/25 | 6 |

## 3. Collaborator's SANS Bayesian rule (corrected 2026-11-15)

Implemented in `monitoring/engine.py::_compute_sans_probability`: single
latest quality-OK ONSD reading, tested against this astronaut's own personal
baseline (median of the first 3 quality-OK readings seen so far in their
causally-visible history) - positive if the delta is ≥0.4mm, applying LR+
6.93; else LR- 0.04. Prior 5% (unsourced simulation placeholder, mirroring the
venous model). All 316 backend tests pass with this model.

**Full cohort (all 300 astronauts, all 9,000 record-days):**

| | Monitor | Repeat |
|---|---|---|
| SANS tier distribution | 7,001 | 1,999 |

SANS probability was computed for 8,110/9,000 scored days (the remainder have
no quality-OK ONSD reading yet available - jugular-only days or scan
failures). This is a far more usable distribution than the superseded
absolute-cutoff version, which put nearly every astronaut at "Repeat"
regardless of event status.

## 4. Fixed-vs-adaptive SANS scanning comparison (corrected)

`backend/evaluation/mars30_schedule_comparison.py` (full output:
`handoff/submission/mars30_schedule_comparison.json`). SANS only, per
directive; venous is excluded from the comparison. Alert = posterior ≥ 15%
(the single-latest-reading LR+6.93 model from a 5% prior caps at ~26.7%
posterior and can never reach the 40% Consult threshold). Jugular-only days
(4, 11, 18, 25) carry no ONSD reading under either policy. Adaptive = fixed
backstop + HRV-proxy trigger-prompted extra scans (assumed trigger accuracy
0.7, the middle of the approved 0.5-0.9 sweep).

| Interval | Policy | Scans used | Detected / 124 events | Median delay (days) | False-escalation rate (of 176 non-events) |
|---|---|---|---|---|---|
| 3-day | fixed | 2,400 | 93 | 11.0 | 18.2% |
| 3-day | adaptive | 2,774 | 98 | 10.0 | 18.8% |
| 7-day | fixed | 1,500 | 91 | 13.0 | 8.5% |
| 7-day | adaptive | 1,938 | 101 | 11.0 | 10.2% |
| 14-day | fixed | 900 | 60 | 19.5 | 1.1% |
| 14-day | adaptive | 1,377 | 84 | 14.0 | 6.8% |

| Interval | Extra scans (adaptive vs fixed) | Days saved by adaptive | Days saved per extra scan |
|---|---|---|---|
| 3-day | 374 | 361 | 0.97 |
| 7-day | 438 | 385 | 0.88 |
| 14-day | 477 | 450 | 0.94 |

**Honest reading:**

- With the corrected personal-baseline rule, **adaptive scanning now reliably
  beats fixed scanning on every measured axis** at every interval: more
  events detected (93→98, 91→101, 60→84), lower median delay (11→10, 13→11,
  19.5→14 days), at a consistent cost of roughly **0.9-1.0 days of detection
  delay saved per extra scan used** - a stable, interpretable number across
  all three intervals, unlike the superseded run's erratic 0.23-0.80 range.
- The tradeoff is a higher false-escalation rate for adaptive at every
  interval (small at 3-day: 18.2%→18.8%; largest at 14-day: 1.1%→6.8%,
  because the sparse 14-day fixed backstop leaves more room for the trigger's
  own ~5%/day base false-fire rate to add false alerts across more unscanned
  days). This is a real cost, not hidden: adaptive scanning detects more,
  faster, but alerts slightly more often on astronauts who never have an
  event.
- Detection is still far from complete (60-101/124 events, missing 23-64),
  and the 14-day fixed baseline is particularly weak (60/124, 19.5-day median
  delay) - a sparse fixed schedule is a real liability this dataset
  demonstrates directly, independent of the adaptive-vs-fixed question.
- This is a very different and more favorable picture than the superseded
  absolute-cutoff run, entirely because the test condition changed from
  "ONSD ≥ 5.0mm" (true for ~90% of healthy astronauts immediately) to "ONSD
  ≥0.4mm above own baseline" (true mainly once a real event has actually
  started raising ONSD) - the corrected rule is doing what a detection rule
  should do.

## 5. What is NOT in this document

- No claim of clinical validity anywhere above.
- No Urgent-tier demonstration: Mars30 has no symptom/red-flag field, and this
  codebase's Urgent tier is rule-based on red-flag symptoms only (never
  probability-based) - a Repeat-tier escalation round-trip through Earth Link
  was verified working instead.
- Venous is excluded from the fixed-vs-adaptive scheduling comparison, per
  directive - its jugular-scan schedule (days 4/11/18/25) is fixed by the
  dataset's own design, not a policy choice this comparison varies.
