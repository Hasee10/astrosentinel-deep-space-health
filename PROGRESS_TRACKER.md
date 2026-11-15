# AstroSentinel — Mars30 Final Submission: Progress Tracker

Base: clean clone of `origin/main` @ `5c8f1c4` (verified, see below). Old working dir and its
uncommitted state are preserved untouched at `D:\shifa_proj\astro-sentinel` (backup copy at
`D:\shifa_proj_backups\astro-sentinel_LOCAL_BACKUP_20261115_173752`, including
`PRE_BACKUP_GIT_STATE.txt`). This clean clone (`astro-sentinel-clean`) is the implementation base.

Status values: VERIFIED COMPLETE / PARTIAL / BLOCKED / NOT STARTED

| # | Task | Status | Notes |
|---|---|---|---|
| 0 | Safe clean clone of origin/main, recovery components verified | VERIFIED COMPLETE | HEAD 5c8f1c4; contracts/evaluation/monitoring/registry/simulation/tests/frontend/handoff all present |
| 1 | Mars30 dataset copied in, run through its own validator | VERIFIED COMPLETE | `python validate_dataset.py` → ALL CHECKS PASSED (9000 rows, 300 astronauts, scenario/split counts match README) |
| 2 | Dataset loader module (backend) | NOT STARTED | |
| 3 | Train/evaluate SANS + venous baseline models on Mars30 | NOT STARTED | reproduce README baseline table first, as regression anchor |
| 4 | Revised SANS probability logic (collaborator spec: per-day probability, personal-baseline features, tiers 15/40/80%) | NOT STARTED | must not reuse research_v1 assumptions/fixtures — separate versioned path |
| 5 | Fixed-vs-adaptive scheduling comparison using Mars30-driven detector | NOT STARTED | reuse existing evaluation/policies.py + sweep.py scaffolding |
| 6 | Slide-ready plots/results | NOT STARTED | |
| 7 | Frontend update (monitoring cards, jugular charts, Research/Results, Earth Link) | NOT STARTED | |
| 8 | Full test suite + public-data safety checks (no PII, no clinical claims) | NOT STARTED | |
| 9 | New submission GitHub repo (destination TBD — see below) | BLOCKED | need repo name/visibility decision; will not push to existing `Hasee10/astro-sentinel` without explicit authorization |
| 10 | Vercel deployment | NOT STARTED | depends on #9 |

## Open blocker
Task 9 needs the new repository's name (and whether it should be created under the same GitHub
account or elsewhere) before a destination exists to push to. Everything up through implementation,
testing, and local verification can proceed without this.
