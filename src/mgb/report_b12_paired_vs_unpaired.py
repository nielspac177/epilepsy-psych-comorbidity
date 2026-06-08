#!/usr/bin/env python3
"""
Reviewer comment B12 (Glaser): selection-bias check.

Are there temporal/clinical differences between patients WITH vs WITHOUT
paired symptom-score data (PHQ-9 and, separately, GAD-7)? If the paired and
unpaired groups look similar, that reassures against selection bias in the
paired-score analyses.

"Paired" definitions:
  - PHQ-9 paired = phq9_baseline AND phq9_followup both non-missing
  - GAD-7 paired = gad7_baseline AND gad7_followup both non-missing

Compared covariates: age, female_n, insurance, svi, followup_years,
seizure_free, Engel score simplified, preop_any_psych_dx.

Tests:
  - continuous (age, svi, followup_years): Welch t-test AND Mann-Whitney U
    (report Mann-Whitney p as primary, non-parametric)
  - categorical/binary (female_n, insurance, seizure_free, Engel,
    preop_any_psych_dx): chi-square; Fisher exact when 2x2 and any
    expected cell < 5.

DATA CAVEAT: This is the currently-available extract. It reproduces the
manuscript's PREOP psychiatric prevalence (~49-51%) but NOT the manuscript's
reported POSTOP decrease (Table 3: 49.1% -> 42.5%); here postop prevalence is
~stable-to-higher. Paired PHQ-9/GAD-7 n is far below the manuscript's 116/112.
Treat all numbers as PROVISIONAL pending the verified Table-3 extract.
"""

import sys
import numpy as np
import pandas as pd
from scipy import stats

CSV = ("/Users/nielspacheco/Desktop/Research/Rolston lab/Psych_epilepsy_surgery/"
       "repro_build/epilepsy-psych-comorbidity/work/mgb_analysis_clean.csv")

INSURANCE = "Insurance (Private, Medicare, Medicaid, Mix, Unknown)"
ENGEL = "Engel score simplified"

CONT = ["age", "svi", "followup_years"]
CAT = ["female_n", INSURANCE, "seizure_free", ENGEL, "preop_any_psych_dx"]


def fmt_p(p):
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return "NA"
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def med_iqr(s):
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) == 0:
        return "NA"
    return f"{s.median():.2f} [{s.quantile(.25):.2f}-{s.quantile(.75):.2f}] (n={len(s)})"


def n_pct(s, positive=1):
    s = s.dropna()
    if len(s) == 0:
        return "NA"
    n = (s == positive).sum()
    return f"{n}/{len(s)} ({100*n/len(s):.1f}%)"


def cont_test(df, col, grp):
    a = pd.to_numeric(df.loc[grp, col], errors="coerce").dropna()
    b = pd.to_numeric(df.loc[~grp, col], errors="coerce").dropna()
    if len(a) < 2 or len(b) < 2:
        return np.nan, np.nan
    _, p_t = stats.ttest_ind(a, b, equal_var=False)
    _, p_mw = stats.mannwhitneyu(a, b, alternative="two-sided")
    return p_t, p_mw


def cat_test(df, col, grp):
    sub = df[[col]].copy()
    sub["grp"] = np.where(grp, "paired", "unpaired")
    sub = sub.dropna(subset=[col])
    ct = pd.crosstab(sub[col].astype(str), sub["grp"])
    if ct.shape[0] < 2 or ct.shape[1] < 2:
        return np.nan, "insufficient"
    if ct.shape == (2, 2):
        exp = stats.chi2_contingency(ct, correction=False)[3]
        if (exp < 5).any():
            _, p = stats.fisher_exact(ct.values)
            return p, "Fisher exact"
    chi2, p, _, _ = stats.chi2_contingency(ct)
    return p, "chi-square"


def run_panel(df, paired_mask, label):
    print("=" * 78)
    print(f"  {label}")
    print(f"  paired n={int(paired_mask.sum())}  |  unpaired n={int((~paired_mask).sum())}")
    print("=" * 78)
    rows = []
    print(f"{'Covariate':<28}{'Paired':<26}{'Unpaired':<26}{'p':>8}  test")
    print("-" * 100)

    for col in CONT:
        p_t, p_mw = cont_test(df, col, paired_mask)
        paired_v = med_iqr(df.loc[paired_mask, col])
        unp_v = med_iqr(df.loc[~paired_mask, col])
        print(f"{col:<28}{paired_v:<26}{unp_v:<26}{fmt_p(p_mw):>8}  Mann-Whitney (t p={fmt_p(p_t)})")
        rows.append((col, paired_v, unp_v, fmt_p(p_mw), "Mann-Whitney"))

    for col in CAT:
        p, test = cat_test(df, col, paired_mask)
        if col in ("female_n", "seizure_free", "preop_any_psych_dx"):
            paired_v = n_pct(df.loc[paired_mask, col])
            unp_v = n_pct(df.loc[~paired_mask, col])
        else:
            # multi-level: show level breakdown compactly
            pv = df.loc[paired_mask, col].dropna().astype(str).value_counts(normalize=True)
            uv = df.loc[~paired_mask, col].dropna().astype(str).value_counts(normalize=True)
            paired_v = "; ".join(f"{k}:{100*v:.0f}%" for k, v in pv.sort_index().items())
            unp_v = "; ".join(f"{k}:{100*v:.0f}%" for k, v in uv.sort_index().items())
        print(f"{col:<28}{paired_v:<26}{unp_v:<26}{fmt_p(p):>8}  {test}")
        rows.append((col, paired_v, unp_v, fmt_p(p), test))
    print()
    return rows


def main():
    df = pd.read_csv(CSV, low_memory=False)
    print(f"Loaded {len(df)} patients (one row per patient).\n")

    phq_paired = df["phq9_baseline"].notna() & df["phq9_followup"].notna()
    gad_paired = df["gad7_baseline"].notna() & df["gad7_followup"].notna()

    run_panel(df, phq_paired, "PHQ-9 PAIRED vs UNPAIRED")
    run_panel(df, gad_paired, "GAD-7 PAIRED vs UNPAIRED")

    print("DATA CAVEAT: currently-available extract. Reproduces preop psych "
          "prevalence (~49-51%) but NOT manuscript postop decrease; paired n is "
          "below manuscript's 116/112. All numbers PROVISIONAL pending verified "
          "Table-3 extract.")


if __name__ == "__main__":
    main()
