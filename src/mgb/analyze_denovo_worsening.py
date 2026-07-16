#!/usr/bin/env python3
"""
Reviewer question (Weisholtz): the manuscript reports only *net* psychiatric
improvement and never shows the patients who get WORSE. This script quantifies
the worsening tail in the MGB cohort:

  - de novo (new-onset) psychiatric disorder: preop-negative -> postop-positive,
    overall and by domain (depression, anxiety, psychosis, substance);
  - worsening by diagnosis count: postop count > preop count;
  - symptom worsening: PHQ-9 increase >= 5, GAD-7 increase >= 4 (paired subset);
  - a composite worsening outcome (mirror of the a-priori `improved` composite);
  - "double burden": not seizure-free AND worsened.

Every rate is reported against MULTIPLE denominators because the postop ICD
columns behave as a cumulative/carry-forward problem list and 105/273 patients
have NO postop record (missing follow-up). These are best-effort / exploratory
estimates, consistent with the trajectory caveats already in the paper.

Reproducible: reads work/mgb_clean_review.csv (built by build_clean_mgb_dataset.py),
writes work/denovo_worsening.json and prints a report.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

DATA = Path(__file__).resolve().parents[2] / "work" / "mgb_clean_review.csv"
OUT = DATA.parent / "denovo_worsening.json"


def rate(num, den):
    return {"n": int(num), "N": int(den), "pct": round(100 * num / den, 1) if den else None}


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = (z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))) / denom
    return [round(100 * (center - half), 1), round(100 * (center + half), 1)]


def new_onset(df, pre, post):
    """preop-negative -> postop-positive. Returns dict across denominators."""
    pre_neg = df[pre] == 0
    onset = (df[pre] == 0) & (df[post] == 1)
    with_rec = df["has_postop_record"] == 1
    return {
        "all_273": rate(onset.sum(), len(df)),
        "all_273_ci": wilson_ci(int(onset.sum()), len(df)),
        "among_preop_negative": rate(onset.sum(), pre_neg.sum()),
        "among_preop_neg_with_postop_record": rate(
            (onset & with_rec).sum(), (pre_neg & with_rec).sum()
        ),
    }


def main():
    df = pd.read_csv(DATA)
    N = len(df)
    out = {"N": N}

    # sanity: denominators
    out["denominators"] = {
        "N_total": N,
        "preop_any_psych_positive": int((df["preop_any_psych"] == 1).sum()),
        "preop_any_psych_negative": int((df["preop_any_psych"] == 0).sum()),
        "has_postop_record": int((df["has_postop_record"] == 1).sum()),
        "no_postop_record": int((df["has_postop_record"] == 0).sum()),
        "paired_phq": int(df["phq9_pre"].notna().sum() if "phq9_pre" in df else 0),
        "paired_gad": int(df["gad7_pre"].notna().sum() if "gad7_pre" in df else 0),
    }

    # ---------- 1. de novo (new-onset) ----------
    out["new_onset"] = {
        "any_psych": new_onset(df, "preop_any_psych", "postop_any_psych"),
        "depression": new_onset(df, "preop_depression", "postop_depression"),
        "anxiety": new_onset(df, "preop_anxiety", "postop_anxiety"),
        "psychosis": new_onset(df, "preop_psychosis", "postop_psychosis"),
        "substance": new_onset(df, "preop_substance", "postop_substance"),
    }
    # cross-check against precomputed column
    direct_any = ((df["preop_any_psych"] == 0) & (df["postop_any_psych"] == 1)).sum()
    out["new_onset"]["_crosscheck_precomputed_col"] = {
        "computed_here": int(direct_any),
        "new_onset_psych_col_sum": int(df["new_onset_psych"].sum()) if "new_onset_psych" in df else None,
        "match": bool(int(direct_any) == int(df["new_onset_psych"].sum())) if "new_onset_psych" in df else None,
    }

    # ---------- 2. worsening by diagnosis count ----------
    inc_active = df["postop_count_active"] > df["preop_psych_count"]
    inc_cumul = df["postop_count_cumul"] > df["preop_psych_count"]
    with_rec = df["has_postop_record"] == 1
    out["dx_count_increase"] = {
        "active_reading_all": rate(inc_active.sum(), N),
        "active_reading_with_postop_record": rate((inc_active & with_rec).sum(), with_rec.sum()),
        "cumulative_reading_all": rate(inc_cumul.sum(), N),
        "note": "active = blank postop cell counts as 0 active dx; cumulative = carry-forward problem list",
    }

    # ---------- 3. symptom worsening (paired) ----------
    sym = {}
    if "phq9_pre" in df and "phq9_post" in df:
        p = df.dropna(subset=["phq9_pre", "phq9_post"]).copy()
        p["chg"] = p["phq9_post"] - p["phq9_pre"]
        sym["phq9"] = {
            "n_paired": int(len(p)),
            "worse_ge5": rate((p["chg"] >= 5).sum(), len(p)),
            "any_increase": rate((p["chg"] > 0).sum(), len(p)),
            "improved_ge5": rate((p["chg"] <= -5).sum(), len(p)),
            "median_change": float(p["chg"].median()) if len(p) else None,
        }
    if "gad7_pre" in df and "gad7_post" in df:
        g = df.dropna(subset=["gad7_pre", "gad7_post"]).copy()
        g["chg"] = g["gad7_post"] - g["gad7_pre"]
        sym["gad7"] = {
            "n_paired": int(len(g)),
            "worse_ge4": rate((g["chg"] >= 4).sum(), len(g)),
            "any_increase": rate((g["chg"] > 0).sum(), len(g)),
            "improved_ge4": rate((g["chg"] <= -4).sum(), len(g)),
            "median_change": float(g["chg"].median()) if len(g) else None,
        }
    out["symptom_worsening"] = sym

    # ---------- 4. composite worsening (mirror of `improved`) ----------
    worse_dx = inc_active
    worse_phq = pd.Series(False, index=df.index)
    worse_gad = pd.Series(False, index=df.index)
    if "phq9_pre" in df:
        chg = df["phq9_post"] - df["phq9_pre"]
        worse_phq = chg >= 5
    if "gad7_pre" in df:
        chgg = df["gad7_post"] - df["gad7_pre"]
        worse_gad = chgg >= 4
    composite_worse = (worse_dx | worse_phq.fillna(False) | worse_gad.fillna(False))
    out["composite_worsening"] = {
        "all_273": rate(composite_worse.sum(), N),
        "all_273_ci": wilson_ci(int(composite_worse.sum()), N),
        "component_counts": {
            "dx_count_increase": int(worse_dx.sum()),
            "phq_worse_ge5": int(worse_phq.fillna(False).sum()),
            "gad_worse_ge4": int(worse_gad.fillna(False).sum()),
        },
        "for_contrast_improved_composite": rate(int(df["improved"].sum()), N),
    }

    # ---------- 5. double burden: not seizure-free AND worsened ----------
    not_sf = df["seizure_free"] == 0
    out["double_burden"] = {
        "not_seizure_free_and_composite_worse": rate((not_sf & composite_worse).sum(), N),
        "among_not_seizure_free": rate((not_sf & composite_worse).sum(), not_sf.sum()),
        "n_not_seizure_free": int(not_sf.sum()),
    }

    # ---------- 6. new-onset by seizure-freedom (is worsening concentrated in non-free?) ----------
    onset_any = (df["preop_any_psych"] == 0) & (df["postop_any_psych"] == 1)
    try:
        tab = pd.crosstab(df["seizure_free"], onset_any)
        # among preop-negative only
        preneg = df[df["preop_any_psych"] == 0]
        on = (preneg["postop_any_psych"] == 1)
        tab2 = pd.crosstab(preneg["seizure_free"], on).reindex(index=[0, 1], columns=[False, True]).fillna(0)
        _, p_fisher = stats.fisher_exact(tab2.values) if tab2.shape == (2, 2) else (None, None)
        out["new_onset_by_seizure_freedom"] = {
            "among_preop_negative": {
                "not_seizure_free": rate(int(tab2.loc[0, True]), int(tab2.loc[0].sum())),
                "seizure_free": rate(int(tab2.loc[1, True]), int(tab2.loc[1].sum())),
                "fisher_p": round(float(p_fisher), 4) if p_fisher is not None else None,
            }
        }
    except Exception as e:
        out["new_onset_by_seizure_freedom"] = {"error": str(e)}

    # ---------- reporting guidance (from adversarial verification) ----------
    # Independent recomputation from raw data CONFIRMED the new-onset counts
    # (46/35/37/5/2) and the PHQ/GAD worsening counts (7/47, 4/39). A skeptic +
    # safety audit classified which numbers are defensible given the carry-forward
    # (cumulative problem-list) nature of the postop ICD columns.
    out["REPORTING_GUIDANCE"] = {
        "SAFE_gold_standard": [
            "PHQ-9 worse>=5: 7/47 (14.9%) vs improved 12/47 (25.5%)",
            "GAD-7 worse>=4: 4/39 (10.3%) vs improved 9/39 (23.1%)",
        ],
        "SAFE_with_caveat": [
            "new-onset any-psych 46/273 (16.8%) and 46/137 (33.6% among preop-negative) "
            "- frame as 'new diagnoses recorded during follow-up', an administrative signal "
            "broadly consistent with prospective de novo ~16% (Ranpariya 2026), NOT incidence",
            "new-onset by domain at all-273 denominator (dep 12.8%, anx 13.6%, "
            "psychosis 1.8%, substance 0.7%)",
            "new-onset by seizure-freedom 39.8% vs 24.1% (p=0.066), report as a TREND; "
            "note differential-surveillance caveat",
        ],
        "NOT_SAFE_carryforward_artifact_do_not_report": [
            "dx_count_increase (29.3/47.6/32.2%)",
            "composite_worsening (31.1%) - 94% driven by dx_count_increase; "
            "spurious 'worsening>improvement' paradox",
            "double_burden (20.1/33.3%) - inherits composite",
            "all 'with_postop_record' denominators (any-psych 92%, domain 39.8%) - "
            "detection/collider bias (has_postop_record = ANY postop ICD, not psych)",
        ],
        "mandatory_caveats": [
            "postop ICD = cumulative/carry-forward problem list (0 F+ -> F-)",
            "105/273 have no postop record (missing follow-up)",
            "de novo defined only among 137 preop-negative; 273 denom includes 136 who cannot be de novo",
            "catch-up coding at a tertiary center may inflate 'new' codes",
        ],
    }

    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
