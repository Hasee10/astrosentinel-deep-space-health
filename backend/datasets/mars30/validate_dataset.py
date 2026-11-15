"""Independent check of the CSVs against the decisions. Reads ONLY the CSV files."""
import sys
import numpy as np
import pandas as pd

d = pd.read_csv(sys.argv[1] + "/astronaut_days.csv")
a = pd.read_csv(sys.argv[1] + "/astronauts.csv")
ok = True

def check(name, cond, detail=""):
    global ok
    ok &= bool(cond)
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail else ""))

check("9000 rows, 300 astronauts x 30 days", len(d) == 9000 and a.astronaut_id.nunique() == 300)
check("unique (astronaut, day)", not d.duplicated(["astronaut_id", "day"]).any())
check("one scan type per day; jugular only on 4/11/18/25",
      set(d[d.scan_type == "jugular"].day) == {4, 11, 18, 25} and (d.groupby("scan_type").size().to_dict() == {"jugular": 1200, "onsd": 7800}))
check("ONSD null on jugular days, jugular null on ONSD days",
      d[d.scan_type == "jugular"].onsd_mm.isna().all() and d[d.scan_type == "onsd"].jugular_area_mm2.isna().all())

# SANS
n_sans = a.has_sans_event.sum(); n_ven = a.has_venous_event.sum()
print(f"     SANS events {n_sans}/300 = {n_sans/300:.1%} (target ~40%), venous events {n_ven}/300 = {n_ven/300:.1%} (target 54.5%)")
check("SANS event rate within 40% +/- 3 SE", abs(n_sans / 300 - 0.40) < 3 * np.sqrt(.4 * .6 / 300))
check("venous event rate within 54.5% +/- 3 SE", abs(n_ven / 300 - 6 / 11) < 3 * np.sqrt(.545 * .455 / 300))
hi = a[a.susceptibility_class == "high"]; lo = a[a.susceptibility_class == "low"]
print(f"     high-susceptibility share {len(hi)/300:.1%} (target 25%); SANS rate high {hi.has_sans_event.mean():.1%} (70%), low {lo.has_sans_event.mean():.1%} (30%)")
check("onset days within 5..20", a.sans_onset_day.dropna().between(5, 20).all() and a.venous_onset_day.dropna().between(5, 20).all())
check("event flag <-> onset present", ((a.has_sans_event == 1) == a.sans_onset_day.notna()).all() and ((a.has_venous_event == 1) == a.venous_onset_day.notna()).all())
check("baseline clipped to 4.8..5.9", a.onsd_baseline_mm.between(4.8, 5.9).all(),
      f"mean {a.onsd_baseline_mm.mean():.3f} sd {a.onsd_baseline_mm.std():.3f}")

# ONSD progression slope and noise, from the latent column vs observed
on = d[(d.scan_type == "onsd") & (d.scan_quality_status == "ok")].merge(a[["astronaut_id", "onsd_baseline_mm", "sans_onset_day"]], on="astronaut_id")
on["resid"] = on.onsd_mm - on.label_true_onsd_mm
check("ONSD within-person noise SD ~0.20", abs(on.resid.std() - 0.20) < 0.01, f"{on.resid.std():.3f}")
post = on[on.label_sans_event_active == 1]
slope = np.polyfit(post.label_sans_days_since_onset.astype(float), (post.onsd_mm - post.onsd_baseline_mm), 1)[0]
check("post-onset ONSD slope ~0.04 mm/day", abs(slope - 0.04) < 0.004, f"{slope:.4f}")
pre = on[(on.label_sans_event_active == 0)]
check("healthy/pre-onset ONSD mean ~ own baseline (no drift)", abs((pre.onsd_mm - pre.onsd_baseline_mm).mean()) < 0.01, f"{(pre.onsd_mm - pre.onsd_baseline_mm).mean():+.4f}")
onsd_days = d[d.scan_type == "onsd"]
st = onsd_days.scan_quality_status.value_counts(normalize=True)
check("ONSD failure injection ~10% (5% degraded, 5% failed)", abs(st.get("degraded", 0) - .05) < .01 and abs(st.get("failed", 0) - .05) < .01, str(st.round(3).to_dict()))
deg = d[d.scan_quality_status == "degraded"]; bias = (deg.onsd_mm - deg.label_true_onsd_mm).mean()
check("off-axis bias ~ +0.4 mm (above noise-only mean)", abs(bias - 0.4) < 0.05, f"{bias:.3f}")
check("failed scans have no ONSD value; others do", d[d.scan_quality_status == "failed"].onsd_mm.isna().all() and d[(d.scan_type == "onsd") & (d.scan_quality_status != "failed")].onsd_mm.notna().all())
check("event onset day: SANS label turns on exactly at onset", all(
    (g.label_sans_event_active.values == (g.day.values >= o)).all()
    for o, g in ((r.sans_onset_day, d[d.astronaut_id == r.astronaut_id]) for r in a[a.has_sans_event == 1].itertuples())))

# venous
jv = d[d.scan_type == "jugular"]
tf = jv.label_true_flow_class; of = jv.jugular_flow_class
check("flow class: antegrade when no event active; stagnant d0-2; retrograde d>=3",
      (tf[jv.label_venous_event_active == 0] == "antegrade").all()
      and (tf[jv.label_venous_days_since_onset.between(0, 2)] == "stagnant").all()
      and (tf[jv.label_venous_days_since_onset >= 3] == "retrograde").all())
check("observed flow class == true (misread rate 0)", (tf == of).all())
tarea = d.label_true_jugular_area_mm2
check("true area: 12 baseline, 34 from onset+5, linear ramp",
      (tarea[d.label_venous_event_active == 0] == 12).all() and (tarea[d.label_venous_days_since_onset >= 5] == 34).all()
      and np.isclose(tarea[d.label_venous_days_since_onset == 2].iloc[0], 12 + 22 * 2 / 5))
ra = (jv.jugular_area_mm2 / jv.label_true_jugular_area_mm2 - 1)
check("jugular area noise ~10% of value", abs(ra.std() - 0.10) < 0.01, f"{ra.std():.3f}")
check("scenario counts add up", a.scenario.value_counts().sum() == 300)
print("     scenarios:", a.scenario.value_counts().to_dict())
print("     splits:", a.split.value_counts().to_dict(), "| scenarios per split:", a.groupby("split").scenario.value_counts().unstack(fill_value=0).to_dict("index"))
check("split by astronaut (no astronaut in two splits)", d.groupby("astronaut_id").split.nunique().max() == 1)

# how many astronauts could a jugular scan ever catch?
first_scan_after = []
for r in a[a.has_venous_event == 1].itertuples():
    s = [x for x in (4, 11, 18, 25) if x >= r.venous_onset_day]
    first_scan_after.append(s[0] - r.venous_onset_day if s else None)
fa = pd.Series(first_scan_after)
print(f"     venous events with NO jugular scan after onset: {fa.isna().sum()}/{len(fa)}; median wait to first scan after onset: {fa.dropna().median():.0f} days (max {fa.max():.0f})")
print("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
