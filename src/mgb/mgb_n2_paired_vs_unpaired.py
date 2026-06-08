#!/usr/bin/env python3
"""
MGB analysis N2 -- Paired vs Unpaired comparison (Glaser et al.)

GOAL
----
Selection-bias / attrition check for the limitations section. "Paired" patients
are those with BOTH a baseline AND a follow-up score (PHQ-9 and, separately,
GAD-7). We compare paired vs unpaired patients on demographics, follow-up
length, seizure outcome, social vulnerability, and baseline psychiatric burden.
If no significant differences emerge, the paired subsample is reassuringly
representative of the full cohort despite its small size.

KNOWN DATA GAP (flagged loudly in output)
-----------------------------------------
PHQ-9 / GAD-7 are sparse in this analytic file. The manuscript's paired
n=116 (PHQ-9) / n=112 (GAD-7) CANNOT be reproduced from this CSV. We report the
ACTUAL available paired n (single digits / low teens). With paired n this small,
the comparison is severely underpowered: "no significant difference" here means
"no difference detectable", NOT "groups are equivalent". Treat as descriptive.

Definitions
-----------
PHQ-9 baseline = 'Baseline PHQ-9'
PHQ-9 follow-up = any non-null among ['PHQ-9', 'PHQ-9.1']
GAD-7 baseline = 'GAD-7'
GAD-7 follow-up = any non-null among ['GAD-7.1', 'GAD-7.2']
paired = has both a baseline AND a follow-up value for that instrument.

Tests
-----
Continuous (age, length of follow-up, SVI_overall): Mann-Whitney U (robust to
small n / non-normality). Welch t-test reported alongside for reference.
Categorical (female, insurance, seizure-free, Engel, subsequent tx,
preop_any_psych_dx): chi-square with Fisher's exact fallback for 2x2 / sparse.
"""

import os
import warnings
import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

CSV = "/Users/nielspacheco/Desktop/Research/Rolston lab/Psych_epilepsy_surgery/results/merged_deprivation_psych_data.csv"

CONT_VARS = {
    "age_at_surgery": "age_at_surgery",
    "Length of follow-up ": "length_of_followup_yrs",
    "SVI_overall": "SVI_overall",
}
CAT_VARS = {
    "female": "female",
    "Insurance (Private, Medicare, Medicaid, Mix, Unknown)": "insurance",
    "Seizure-free at last follow-up?": "seizure_free",
    "Engel score simplified": "engel_simplified",
    "Subsequent treatment? (y/n)": "subsequent_treatment",
    "preop_any_psych_dx": "preop_any_psych_dx",
}


def num(s):
    return pd.to_numeric(s, errors="coerce")


def build_paired_flag(df, baseline_col, followup_cols):
    base = num(df[baseline_col])
    fu = pd.Series(False, index=df.index)
    for c in followup_cols:
        fu = fu | num(df[c]).notna()
    return base.notna() & fu


def compare_continuous(df, group, src_col):
    a = num(df.loc[group, src_col]).dropna()
    b = num(df.loc[~group, src_col]).dropna()
    na, nb = len(a), len(b)
    out = {"var": src_col, "type": "continuous", "n_paired": na,
           "n_unpaired": nb, "median_paired": np.nan, "median_unpaired": np.nan,
           "test": "Mann-Whitney U", "p": np.nan, "welch_p": np.nan, "note": ""}
    if na < 2 or nb < 2:
        out["note"] = "insufficient n"
        return out
    out["median_paired"] = round(float(a.median()), 3)
    out["median_unpaired"] = round(float(b.median()), 3)
    try:
        out["p"] = float(stats.mannwhitneyu(a, b, alternative="two-sided")[1])
    except Exception as e:
        out["note"] = f"MWU fail: {e}"
    try:
        out["welch_p"] = float(stats.ttest_ind(a, b, equal_var=False)[1])
    except Exception:
        pass
    return out


def compare_categorical(df, group, src_col):
    sub = df[[src_col]].copy()
    sub["_paired"] = np.where(group, "paired", "unpaired")
    sub = sub.dropna(subset=[src_col])
    sub[src_col] = sub[src_col].astype(str).str.strip()
    out = {"var": src_col, "type": "categorical",
           "n_paired": int((sub["_paired"] == "paired").sum()),
           "n_unpaired": int((sub["_paired"] == "unpaired").sum()),
           "test": "", "p": np.nan, "note": ""}
    if out["n_paired"] < 1 or out["n_unpaired"] < 1:
        out["note"] = "insufficient n"
        return out
    tab = pd.crosstab(sub[src_col], sub["_paired"])
    if tab.shape[0] < 2:
        out["note"] = "only one level present"
        return out
    if tab.shape == (2, 2):
        out["test"] = "Fisher exact"
        try:
            out["p"] = float(stats.fisher_exact(tab.values)[1])
        except Exception as e:
            out["note"] = f"fisher fail: {e}"
    else:
        try:
            chi2, p, dof, exp = stats.chi2_contingency(tab.values)
            out["test"] = "chi-square"
            out["p"] = float(p)
            if (exp < 5).mean() > 0.2:
                out["note"] = ">20% expected cells <5 (chi-square unreliable; "
                out["note"] += "interpret with caution)"
        except Exception as e:
            out["note"] = f"chi2 fail: {e}"
    return out


def run_instrument(df, label, baseline_col, followup_cols):
    paired = build_paired_flag(df, baseline_col, followup_cols)
    n_paired = int(paired.sum())
    n_unpaired = int((~paired).sum())
    print("\n" + "=" * 78)
    print(f"INSTRUMENT: {label}")
    print(f"  baseline col   : {baseline_col!r}")
    print(f"  follow-up cols : {followup_cols}")
    print(f"  PAIRED (baseline + >=1 follow-up) n = {n_paired}")
    print(f"  UNPAIRED                          n = {n_unpaired}")
    print(f"  manuscript paired n target = "
          f"{'116 (PHQ-9)' if 'PHQ' in label else '112 (GAD-7)'} "
          f"-> NOT reproducible from this file (see DATA GAP).")
    print("=" * 78)

    rows = []
    for src in CONT_VARS:
        rows.append(compare_continuous(df, paired, src))
    for src in CAT_VARS:
        rows.append(compare_categorical(df, paired, src))
    res = pd.DataFrame(rows)
    res["instrument"] = label
    res["paired_n"] = n_paired
    res["unpaired_n"] = n_unpaired

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)
    show = res[["var", "type", "test", "n_paired", "n_unpaired", "p",
                "median_paired", "median_unpaired", "note"]].copy()
    show["p"] = show["p"].map(lambda v: f"{v:.4f}" if pd.notna(v) else "NA")
    print(show.to_string(index=False))

    sig = res[(res["p"].notna()) & (res["p"] < 0.05)]
    if len(sig):
        print("\n  *** SIGNIFICANT (p<0.05) differences:")
        for _, r in sig.iterrows():
            print(f"      - {r['var']}: {r['test']} p={r['p']:.4f}")
    else:
        print("\n  No variable reached p<0.05 (paired vs unpaired). "
              "Caveat: tiny n -> underpowered; absence of evidence != equivalence.")
    return res


def main():
    df = pd.read_csv(CSV)
    print(f"Loaded: {CSV}")
    print(f"Rows: {len(df)}  Cols: {df.shape[1]}")
    print("\nScore-column non-null availability:")
    for c in ["Baseline PHQ-9", "PHQ-9", "PHQ-9.1",
              "GAD-7", "GAD-7.1", "GAD-7.2"]:
        print(f"  {c:>18s}: {df[c].notna().sum():>4d} non-null")

    all_res = []
    all_res.append(run_instrument(df, "PHQ-9", "Baseline PHQ-9",
                                  ["PHQ-9", "PHQ-9.1"]))
    all_res.append(run_instrument(df, "GAD-7", "GAD-7",
                                  ["GAD-7.1", "GAD-7.2"]))

    out = pd.concat(all_res, ignore_index=True)
    out_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "mgb_n2_paired_vs_unpaired_results.csv")
    out.to_csv(out_csv, index=False)
    print("\n" + "=" * 78)
    print("CAVEATS")
    print("=" * 78)
    print("- DATA GAP: manuscript paired n=116/112 NOT reproducible here; "
          "actual paired n is single digits / low teens.")
    print("- Underpowered: with paired n this small, non-significant p-values "
          "do NOT establish equivalence (Type II error very likely).")
    print("- Chi-square on sparse categorical tables is unreliable; Fisher "
          "used for 2x2, flags noted above.")
    print(f"\nResults table written: {out_csv}")


if __name__ == "__main__":
    main()
