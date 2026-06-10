#!/usr/bin/env python3
"""
Build ONE clean, reviewable MGB analysis dataset for the postoperative
psychiatric-improvement analysis, including the treatment-type question (Adam).

Design goals
------------
1. Reviewable: one row per patient (keyed on MRN), human-readable columns, with
   every improvement *component* exposed separately so a manual chart review can
   check each one. Nothing is hidden inside a composite.
2. Faithful to the manuscript's a-priori definition. Psychiatric improvement is
   the model outcome and is defined as ANY of:
       (a) a net decrease in the NUMBER of psychiatric diagnoses postoperatively,
       (b) a PHQ-9 reduction >= 5 points,
       (c) a GAD-7 reduction >= 4 points.
   (Methods, "Psychiatric improvement ... was defined a priori as ...".)
3. Transparent about the post-op diagnosis question. The post-op ICD columns
   behave like a cumulative problem list, so we expose BOTH readings:
       postop_count_active  -- # post-op psych F-codes (blank cell = 0 active dx)
       postop_count_cumul   -- the merged-file cumulative count
   so the reviewer can decide which matches the chart. imp_dx is computed from the
   ACTIVE reading (the one consistent with observing resolution / a decrease).

Inputs (institutional extract only; never committed):
    results/merged_deprivation_psych_data.csv   -- base: demographics, SVI, raw ICD
    Epilepsy_surgery_rohan_dataset_v1.xlsx       -- 'ASM analysis': PHQ-9/GAD-7 scores

Outputs (local, git-ignored; contain MRN):
    work/mgb_clean_review.csv                    -- the analysis dataset
    work/mgb_clean_review_dictionary.md          -- data dictionary + summary
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/Users/nielspacheco/Desktop/Research/Rolston lab/Psych_epilepsy_surgery")
MERGED = ROOT / "results" / "merged_deprivation_psych_data.csv"
ROHAN = ROOT / "Epilepsy_surgery_rohan_dataset_v1.xlsx"
OUT = Path(__file__).resolve().parents[2] / "work"
OUT.mkdir(exist_ok=True)

# Psychiatric ICD-10 prefixes, grouped. Any F-code counts toward "any psych".
PSYCH_GROUPS = {
    "depression": ("F32", "F33", "F34", "F31", "F39"),
    "anxiety": ("F40", "F41", "F43", "F42", "F48"),
    "psychosis": ("F20", "F22", "F23", "F25", "F28", "F29"),
    "substance": ("F10", "F11", "F12", "F13", "F14", "F15", "F16", "F17", "F18", "F19"),
    "neurodevelopmental": ("F80", "F81", "F84", "F90", "F91", "F95"),
    "organic_mood": ("F06",),
}
ALL_PSYCH_PREFIXES = tuple(p for g in PSYCH_GROUPS.values() for p in g)


def parse_score(x) -> float:
    """Bracket-aware numeric parse: '[13]' -> 13.0, '12' -> 12.0, '' -> nan."""
    if pd.isna(x):
        return np.nan
    s = str(x).strip().strip("[]").strip()
    m = re.search(r"-?\d+\.?\d*", s)
    return float(m.group()) if m else np.nan


def code_is(prefixes):
    def fn(v) -> bool:
        if pd.isna(v):
            return False
        c = str(v).upper().replace(".", "").strip()
        return any(c.startswith(p) for p in prefixes)
    return fn


def count_codes(row, prefixes) -> int:
    return int(sum(code_is(prefixes)(v) for v in row))


def any_code(row, prefixes) -> int:
    return int(any(code_is(prefixes)(v) for v in row))


def main() -> int:
    if not MERGED.exists() or not ROHAN.exists():
        sys.exit("Source MGB files not found; runs on the institutional extract only.")

    base = pd.read_csv(MERGED, dtype=str)
    # reset_index is REQUIRED: after filtering/dedup the row index is gapped, and
    # several columns below are assigned to `df` by index. Without reset_index those
    # assignments misalign (pandas aligns on the gapped index), scrambling per-patient
    # values. Resetting to 0..N-1 makes index- and position-based assignment identical.
    base = base[base["MRN"].notna()].drop_duplicates(subset="MRN", keep="first").reset_index(drop=True)

    rohan = pd.read_excel(ROHAN, sheet_name="ASM analysis", dtype=str)
    rohan = rohan[rohan["MRN"].notna()].drop_duplicates(subset="MRN", keep="first").reset_index(drop=True)

    df = pd.DataFrame({"MRN": base["MRN"].values})

    # ---- demographics ------------------------------------------------------
    df["female"] = pd.to_numeric(base["female"], errors="coerce")
    df["age_at_surgery"] = pd.to_numeric(base["age_at_surgery"], errors="coerce")
    df["race_ethnicity"] = base.get("Race/ethnicity")
    ins = base["Insurance (Private, Medicare, Medicaid, Mix, Unknown)"].astype(str).str.strip().str.lower()
    df["insurance_raw"] = base["Insurance (Private, Medicare, Medicaid, Mix, Unknown)"].values
    df["insurance_public"] = ins.isin(["medicare", "medicaid", "mix"]).astype(int)

    # ---- epilepsy ----------------------------------------------------------
    df["etiology"] = base.get("Presumed Etiology of Seizures")
    df["epilepsy_duration"] = pd.to_numeric(base.get("epilepsy_duration"), errors="coerce")
    df["preop_aeds"] = pd.to_numeric(base.get("Preop # AEDs"), errors="coerce")

    # ---- treatment type ----------------------------------------------------
    # Neuromodulation (RNS/DBS/VNS) vs resective/ablative (resection/LITT). Patients
    # without a recorded definitive type are classified as resective/ablative, the
    # default epilepsy-surgery procedure; there is no separate "none/unknown" group.
    ttype = base.get("Subsequent Treatment Type").astype(str).str.strip()
    df["treatment_type"] = ttype.where(ttype.isin(["Resection", "LITT", "RNS", "DBS", "VNS", "MST"]),
                                       "Resection")
    grp = base.get("Subsequent Resection vs. Neuromod").astype(str).str.strip().str.upper()
    df["treatment_group"] = np.where(grp == "NEUROMOD", "NEUROMOD", "RES_ABLATIVE")

    # ---- seizure outcome ---------------------------------------------------
    df["seizure_free"] = (base["Seizure-free at last follow-up?"].astype(str)
                          .str.strip().str.lower().eq("y").astype(int))
    df["engel_simplified"] = base.get("Engel score simplified")
    # favorable seizure outcome = Engel I or II (a clinically meaningful reduction)
    eng = base.get("Engel score simplified").astype(str).str.strip().str.upper()
    df["seizure_improved"] = eng.isin(["I", "II"]).astype(int)
    df["delta_seizure_freq"] = pd.to_numeric(base.get("Delta Seizure Frequency"), errors="coerce")
    df["followup_years"] = pd.to_numeric(base.get("Length of follow-up "), errors="coerce")

    # ---- number of treatments (therapeutic procedures) ---------------------
    def yn01(col):
        return pd.to_numeric(base.get(col), errors="coerce").fillna(0).clip(0, 1)
    prior_res = yn01("Prior resective intervention? 0=no, 1= yes")
    prior_oth = yn01("Prior other interventions? 0=no, 1= yes")
    definitive = base["Subsequent treatment? (y/n)"].astype(str).str.strip().str.lower().eq("y").astype(int)
    # Every patient underwent at least one therapeutic epilepsy operation (the index
    # procedure), so the count is floored at 1; prior and additional procedures add to it.
    n = prior_res.values + prior_oth.values + definitive.values
    df["n_treatments"] = np.clip(n, 1, None).astype(int)
    df["multiple_treatments"] = (df["n_treatments"] >= 2).astype(int)

    # ---- social vulnerability (scale to 0-1 if stored as 0-100) ------------
    svi = pd.to_numeric(base.get("SVI_overall"), errors="coerce")
    if svi.max(skipna=True) and svi.max(skipna=True) > 1.5:
        svi = svi / 100.0
    df["svi_overall"] = svi

    # ---- psychiatric diagnoses: preop vs postop (ACTIVE reading) -----------
    pre_cols = [c for c in base.columns if re.match(r"ICD_10_\d+ \(DSM-5 AXIS\)", c)]
    post_cols = [c for c in base.columns if "Post-op last follow" in c and "AXIS" in c]

    df["preop_any_psych"] = base[pre_cols].apply(lambda r: any_code(r.values, ALL_PSYCH_PREFIXES), axis=1).values
    df["preop_psych_count"] = base[pre_cols].apply(lambda r: count_codes(r.values, ALL_PSYCH_PREFIXES), axis=1).values
    # ACTIVE post-op reading: a blank post-op cell = 0 active psychiatric diagnoses
    df["postop_any_psych"] = base[post_cols].apply(lambda r: any_code(r.values, ALL_PSYCH_PREFIXES), axis=1).values
    df["postop_count_active"] = base[post_cols].apply(lambda r: count_codes(r.values, ALL_PSYCH_PREFIXES), axis=1).values
    # CUMULATIVE reading carried from the merged file, for comparison only
    df["postop_count_cumul"] = pd.to_numeric(base.get("postop_psych_count"), errors="coerce").values
    df["has_postop_record"] = base[post_cols].notna().any(axis=1).astype(int).values

    for label, prefixes in PSYCH_GROUPS.items():
        df[f"preop_{label}"] = base[pre_cols].apply(lambda r: any_code(r.values, prefixes), axis=1).values
        df[f"postop_{label}"] = base[post_cols].apply(lambda r: any_code(r.values, prefixes), axis=1).values

    # transitions (active reading)
    df["new_onset_psych"] = ((df["preop_any_psych"] == 0) & (df["postop_any_psych"] == 1)).astype(int)
    df["resolved_psych"] = ((df["preop_any_psych"] == 1) & (df["postop_any_psych"] == 0)).astype(int)

    # ---- PHQ-9 / GAD-7 (re-parsed bracket-aware from rohan) ----------------
    scores = pd.DataFrame({"MRN": rohan["MRN"].values})
    scores["phq9_pre"] = rohan["Baseline PHQ-9"].map(parse_score).fillna(rohan["PHQ-9"].map(parse_score))
    scores["phq9_post"] = rohan["PHQ-9.1"].map(parse_score)
    scores["gad7_pre"] = rohan["GAD-7"].map(parse_score).fillna(rohan["GAD-7.1"].map(parse_score))
    scores["gad7_post"] = rohan["GAD-7.2"].map(parse_score)
    df = df.merge(scores, on="MRN", how="left")
    df["phq9_drop"] = df["phq9_pre"] - df["phq9_post"]
    df["gad7_drop"] = df["gad7_pre"] - df["gad7_post"]

    # ---- improvement components + composite (manuscript MCID: PHQ>=5, GAD>=4) ----
    df["imp_dx"] = (df["postop_count_active"] < df["preop_psych_count"]).astype(int)
    df["imp_phq"] = np.where(df["phq9_drop"].notna(), (df["phq9_drop"] >= 5), np.nan)
    df["imp_phq"] = pd.array(df["imp_phq"], dtype="Int64")
    df["imp_gad"] = np.where(df["gad7_drop"].notna(), (df["gad7_drop"] >= 4), np.nan)
    df["imp_gad"] = pd.array(df["imp_gad"], dtype="Int64")
    # composite: improved if ANY component is true; components that are NaN do not block
    comp = pd.concat([
        df["imp_dx"].astype(float),
        df["imp_phq"].astype(float),
        df["imp_gad"].astype(float),
    ], axis=1)
    df["improved"] = (comp.max(axis=1, skipna=True) >= 1).astype(int)

    df.to_csv(OUT / "mgb_clean_review.csv", index=False)
    _write_dictionary(df)

    # ---- console summary for quick review ----------------------------------
    n = len(df)
    print(f"Wrote {OUT/'mgb_clean_review.csv'}  rows={n}")
    print("\n--- prevalence (active reading) ---")
    print(f"preop any psych : {df['preop_any_psych'].sum()}/{n} = {100*df['preop_any_psych'].mean():.1f}%")
    print(f"postop any psych: {df['postop_any_psych'].sum()}/{n} = {100*df['postop_any_psych'].mean():.1f}%")
    print(f"new-onset={df['new_onset_psych'].sum()}  resolved={df['resolved_psych'].sum()}  "
          f"no-postop-record={n - df['has_postop_record'].sum()}")
    print("\n--- improvement components ---")
    print(f"imp_dx (count decrease, active): {df['imp_dx'].sum()}")
    print(f"imp_phq (PHQ drop>=5): {int(df['imp_phq'].sum())} of {df['imp_phq'].notna().sum()} with paired PHQ")
    print(f"imp_gad (GAD drop>=4): {int(df['imp_gad'].sum())} of {df['imp_gad'].notna().sum()} with paired GAD")
    print(f"COMPOSITE improved: {df['improved'].sum()}/{n} = {100*df['improved'].mean():.1f}%")
    print("\n--- treatment groups ---")
    print(df["treatment_group"].value_counts(dropna=False).to_string())
    return 0


def _write_dictionary(df: pd.DataFrame) -> None:
    lines = [
        "# MGB clean analysis dataset - data dictionary",
        "",
        "One row per patient (keyed on MRN). Built by `build_clean_mgb_dataset.py`.",
        "",
        "## Improvement outcome (manuscript a-priori composite)",
        "`improved` = 1 if ANY of: `imp_dx` (postop psych dx count < preop count),",
        "`imp_phq` (PHQ-9 drop >= 5), or `imp_gad` (GAD-7 drop >= 4).",
        "",
        "## Post-op diagnosis: two readings (review which matches the chart)",
        "- `postop_count_active`: # post-op psychiatric F-codes; a blank cell = 0 active diagnoses.",
        "- `postop_count_cumul`: cumulative count from the merged file (carry-forward problem list).",
        "`imp_dx` uses the ACTIVE reading.",
        "",
        "## Columns",
    ]
    for c in df.columns:
        nonnull = df[c].notna().sum()
        lines.append(f"- `{c}` (n={nonnull})")
    (OUT / "mgb_clean_review_dictionary.md").write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
