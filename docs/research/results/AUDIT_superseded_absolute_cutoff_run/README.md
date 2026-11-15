# SUPERSEDED — absolute 5.0mm cutoff run (audit record only)

**Do not present any number in this folder as the final study.** These files
are the outputs of an earlier, incorrect implementation of the SANS Bayesian
rule, which tested the latest valid ONSD against an **absolute 5.0mm cutoff**.

The collaborator's actual specification (relayed 2026-11-15) is a
**personal-baseline-relative** rule: positive when the latest valid ONSD is at
least 0.4mm above that astronaut's own causally-estimated baseline. The
absolute-cutoff version was a misreading of the originally-approved
`onsd_accuracy_koziarz_2019_rev1` parameter's cutoff value as a monitoring
test condition, rather than correctly using it only as the source of the
LR+/LR- numbers for a differently-specified test.

Kept here only so the correction is auditable - what changed, and why the
originally-reported ~96-99% false-escalation rate was wrong for the requested
model. See `docs/research/results/RESULTS_FOR_SLIDES.md` (repository root
version, not this folder) for the corrected, final figures.
