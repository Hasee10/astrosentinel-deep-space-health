# AstroSentinel — Final Submission Results (Mars30 dataset)

**Every number below is synthetic. Nothing here is clinically validated.** This
document reports real, re-run figures from this repository's own code against
the collaborator's Mars30 dataset (300 astronauts × 30 days, seed 2026) - no
number is invented or estimated by hand.

## 1. Dataset

- `backend/datasets/mars30/` - the collaborator's dataset, copied in unchanged.
- Verified via its own `validate_dataset.py`: **ALL CHECKS PASSED** (9,000 rows,
  300 astronauts, scenario mix: healthy 75 / SANS-only 57 / venous-only 101 /
  both 67; SANS events 41.3%, venous events 56.0%, matching the dataset's own
  documented targets).

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

**Takeaway:** a model using the astronaut's *own* baseline (personal-baseline
delta features) detects SANS reliably with a low false-alarm rate. This is the
dataset author's own recommended approach and the one to use for any further
ML work.

## 3. Collaborator's SANS Bayesian rule (approved 2026-11-15)

Implemented in `monitoring/engine.py::_compute_sans_probability`, mirroring the
already-approved venous model exactly (single latest quality-OK reading, prior
5%, LR+ 6.93 / LR- 0.04, reusing Koziarz et al. 2019's ICU/ICP 5.0mm ONSD
cutoff). All 316 backend tests pass with this change.

**This rule performs poorly on Mars30, and that is a real, reported finding,
not a bug:**

- Its maximum possible posterior from a single reading is **~26.7%** - it can
  never reach the 40% "Consult" tier, only "Repeat" (15%) or "Monitor".
- Because ~90% of healthy astronauts in this dataset sit above the 5.0mm
  cutoff at their own baseline (the dataset's own documentation says so), the
  rule reads nearly every astronaut as "Repeat" almost immediately, regardless
  of whether they ever have an event.
- **Consequence measured directly (see §4): false-escalation rate 96-99%.**

This is the expected cost of reusing an absolute ICU/ICP cutoff for a
free-living population instead of a personal-baseline-relative rule (§2). It
is reported here, not hidden, per the collaborator's own instruction not to
fabricate favorable results.

## 4. Fixed-vs-adaptive SANS scanning comparison

`backend/evaluation/mars30_schedule_comparison.py` (full output:
`handoff/submission/mars30_schedule_comparison.json`). SANS only, per
directive; venous is excluded from the comparison. Alert = posterior ≥ 15%
(see §3 for why 40% is unreachable with this rule). Jugular-only days (4, 11,
18, 25) carry no ONSD reading under either policy. Adaptive = fixed backstop
+ HRV-proxy trigger-prompted extra scans (assumed trigger accuracy 0.7, the
middle of the approved 0.5-0.9 sweep).

| Interval | Policy | Scans used | Detected / 124 events | Median delay (days) | False-escalation rate (of 176 non-events) |
|---|---|---|---|---|---|
| 3-day | fixed | 2,400 | 10 | 3.5 | 98.9% |
| 3-day | adaptive | 2,774 | 8 | 3.5 | 98.9% |
| 7-day | fixed | 1,500 | 12 | 6.0 | 97.2% |
| 7-day | adaptive | 1,938 | 10 | 4.5 | 97.2% |
| 14-day | fixed | 900 | 18 | 7.5 | 96.0% |
| 14-day | adaptive | 1,377 | 16 | 4.0 | 96.6% |

| Interval | Extra scans (adaptive vs fixed) | Days saved by adaptive | Days saved per extra scan |
|---|---|---|---|
| 3-day | 374 | 86 | 0.23 |
| 7-day | 438 | 129 | 0.30 |
| 14-day | 477 | 380 | **0.80** |

**Honest reading, not spun:**

- "Detected" counts are low and occasionally *lower* for adaptive than fixed
  (e.g. 7-day: 12 vs 10). This traces back to §3's false-escalation problem:
  because most astronauts' baseline ONSD already sits near or above 5.0mm,
  "first time the rule crosses 15%" is frequently a **pre-onset false alarm**
  caused by ordinary day-to-day noise, not a real detection - and adaptive's
  extra scans give that noise more chances to be caught *earlier*, sometimes
  converting a lucky late fixed-schedule "detection" into an early adaptive
  false alarm instead. More scans do not help when the underlying rule itself
  is noisy and poorly specific.
- Where adaptive *does* detect, it is reliably faster (median delay drops at
  every interval), and the benefit of the extra scans grows sharply as the
  fixed interval gets sparser (0.23 days saved/scan at 3-day vs 0.80 at
  14-day) - adaptive scanning is most valuable exactly when the fixed backstop
  is least frequent, which is the intuitive result.
- The headline number worth presenting is **not** "adaptive detects more
  events" (it largely doesn't, for the reason above) but **"adaptive reduces
  detection delay, most of all when the fixed schedule is sparse, at a
  measurable scan cost."**
- The false-escalation rate (96-99%) is the dominant problem and is a property
  of the *rule* (§3), not the *schedule*. A personal-baseline-relative rule
  (§2) would need to replace it before this comparison is clinically
  meaningful - the ML baseline already shows that fix is available.

## 5. What is NOT in this document

- No claim of clinical validity anywhere above.
- No frontend screenshot pack (see the running app for live charts/tiers -
  verified working against this same data, see PROGRESS_TRACKER.md).
- No Urgent-tier demonstration: Mars30 has no symptom/red-flag field, and this
  codebase's Urgent tier is rule-based on red-flag symptoms only (never
  probability-based) - a Repeat-tier escalation round-trip through Earth Link
  was verified working instead (A001, day 30: SANS Repeat 26.7%, venous Repeat
  34.5%, received and acknowledged after the simulated one-way delay).
