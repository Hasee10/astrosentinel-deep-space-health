#!/usr/bin/env python3
"""Reference baseline for the ASTROSENTINEL synthetic dataset. Run from this folder:

    python baseline_example.py

Purpose: show the intended train/val/test protocol and give the ML teammate a bar to beat.
It is NOT the project's model. Results measure how well a model recovers the *synthetic
generator's rules*, not clinical performance.

Rules this script follows (and your model must too):
  * Features are CAUSAL: row (astronaut, day) uses only observations from days <= day.
  * Only observed columns are inputs. label_* columns and astronauts.csv are never inputs.
  * Split by astronaut (the `split` column). Threshold chosen on val, reported on test.
  * SANS and venous are modelled separately. No combined score.
"""
from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
FLOWS = {"antegrade": 0, "stagnant": 1, "retrograde": 2}
BASELINE_WINDOW_DAYS = 4  # days 1-4 are event-free by construction (onsets start at day 5)


def causal_features(days: pd.DataFrame) -> pd.DataFrame:
    out = []
    for aid, g in days.sort_values(["astronaut_id", "day"]).groupby("astronaut_id"):
        ok = []  # (day, onsd) for quality-ok ONSD scans seen so far
        last_flow, last_area, last_jug_day = np.nan, np.nan, np.nan
        for r in g.itertuples():
            if r.scan_type == "onsd" and r.scan_quality_status == "ok":
                ok.append((r.day, r.onsd_mm))
            if r.scan_type == "jugular":
                last_flow, last_area, last_jug_day = FLOWS[r.jugular_flow_class], r.jugular_area_mm2, r.day
            early = [v for d, v in ok if d <= BASELINE_WINDOW_DAYS]
            base = np.median(early) if early else np.nan
            vals = [v for _, v in ok]
            last = vals[-1] if vals else np.nan
            last3 = np.mean(vals[-3:]) if vals else np.nan
            if len(ok) >= 3:
                xs, ys = np.array([d for d, _ in ok[-5:]], float), np.array([v for _, v in ok[-5:]], float)
                slope = np.polyfit(xs, ys, 1)[0] if len(xs) >= 3 and np.ptp(xs) > 0 else 0.0
            else:
                slope = 0.0
            out.append(dict(
                astronaut_id=aid, day=r.day,
                onsd_delta_last=last - base, onsd_delta_last3=last3 - base, onsd_slope5=slope,
                n_ok_onsd=len(ok), day_f=r.day,
                have_jugular=float(not np.isnan(last_flow)),
                jug_flow=0 if np.isnan(last_flow) else last_flow,
                jug_area=12.0 if np.isnan(last_area) else last_area,
                jug_age=0 if np.isnan(last_jug_day) else r.day - last_jug_day,
            ))
    return pd.DataFrame(out)


def alert_metrics(df: pd.DataFrame, score: np.ndarray, thr: float, label_col: str, onset_col: str) -> dict:
    """Per-astronaut view: alert = first day score >= thr."""
    d = df.assign(score=score)
    healthy = d[d[onset_col].isna()].groupby("astronaut_id").score.max()
    far = float((healthy >= thr).mean()) if len(healthy) else float("nan")
    delays, missed = [], 0
    for aid, g in d[d[onset_col].notna()].groupby("astronaut_id"):
        onset = g[onset_col].iloc[0]
        hit = g[(g.score >= thr) & (g.day >= onset)]
        if hit.empty:
            missed += 1
        else:
            delays.append(int(hit.day.min() - onset))
    n_ev = d[d[onset_col].notna()].astronaut_id.nunique()
    return dict(false_alarm_astronaut_rate=round(far, 3), detected=f"{n_ev - missed}/{n_ev}",
                median_delay_days=float(np.median(delays)) if delays else None,
                mean_delay_days=round(float(np.mean(delays)), 2) if delays else None)


def pick_threshold(df_val, score_val, onset_col, max_far=0.05):
    d = df_val.assign(score=score_val)
    healthy = d[d[onset_col].isna()].groupby("astronaut_id").score.max()
    return float(np.quantile(healthy, 1 - max_far)) + 1e-9


def run_task(name, df, feats, label_col, onset_col, rule_score_col):
    tr, va, te = (df[df.split == s] for s in ("train", "val", "test"))
    res = {}
    models = {
        "logistic": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
        "grad_boost": HistGradientBoostingClassifier(max_depth=3, learning_rate=0.1, max_iter=150, random_state=0),
    }
    scores = {k: m.fit(tr[feats].fillna(0), tr[label_col]).predict_proba(te[feats].fillna(0))[:, 1] for k, m in models.items()}
    val_scores = {k: models[k].predict_proba(va[feats].fillna(0))[:, 1] for k in models}
    scores["hand_rule"] = te[rule_score_col].fillna(0).to_numpy()
    val_scores["hand_rule"] = va[rule_score_col].fillna(0).to_numpy()
    for k in scores:
        thr = pick_threshold(va, val_scores[k], onset_col)
        res[k] = dict(
            test_auroc=round(roc_auc_score(te[label_col], scores[k]), 3),
            test_avg_precision=round(average_precision_score(te[label_col], scores[k]), 3),
            **alert_metrics(te, scores[k], thr, label_col, onset_col),
        )
    print(f"\n== {name}: test astronauts = {te.astronaut_id.nunique()}, event base rate (rows) = {te[label_col].mean():.2f}")
    print(pd.DataFrame(res).T.to_string())
    return res


def main() -> None:
    days = pd.read_csv("astronaut_days.csv")
    astro = pd.read_csv("astronauts.csv")
    feats = causal_features(days)
    df = days.merge(feats, on=["astronaut_id", "day"]).merge(
        astro[["astronaut_id", "sans_onset_day", "venous_onset_day"]], on="astronaut_id")  # onset only for scoring alerts, never as input

    # hand rules (what the existing Bayesian layer approximates)
    df["rule_sans"] = df["onsd_delta_last"]  # latest valid reading vs own baseline
    df["rule_venous"] = df["jug_flow"].map({0: 0.3, 1: 4.0, 2: 10.0}) * (df["have_jugular"] == 1)  # approved LRs, latest scan only

    sans_feats = ["onsd_delta_last", "onsd_delta_last3", "onsd_slope5", "n_ok_onsd", "day_f"]
    ven_feats = ["have_jugular", "jug_flow", "jug_area", "jug_age", "day_f"]
    out = {
        "sans": run_task("SANS state (ONSD)", df, sans_feats, "label_sans_event_active", "sans_onset_day", "rule_sans"),
        "venous": run_task("Venous state (jugular)", df, ven_feats, "label_venous_event_active", "venous_onset_day", "rule_venous"),
    }
    json.dump(out, open("baseline_results.json", "w"), indent=2)
    print("\nThreshold per model is chosen on VAL so <=5% of event-free astronauts ever alert; numbers above are TEST.")


if __name__ == "__main__":
    main()
