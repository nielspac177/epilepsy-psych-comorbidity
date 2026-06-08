#!/usr/bin/env python3
"""
Assemble one clean MGB analysis dataset for the postoperative-trajectory and
symptom-improvement analyses (reviewer comments B11/B12/B13).

Why this is needed: the working file `merged_deprivation_psych_data.csv` lost the
bracketed follow-up PHQ-9/GAD-7 scores (e.g. "[13]") during an earlier numeric
merge. This script re-parses those scores from the source workbook's "ASM
analysis" sheet and joins them, on MRN, to the covariates, psychiatric flags, and
post-op follow-up ICD columns from the merged file. It also derives a
point-prevalence post-op psychiatric flag from the post-op follow-up ICD columns
(distinct from the cumulative `postop_any_psych_dx` flag) and a multiple-procedure
flag from the prior-intervention columns.

Output (local, git-ignored; contains MRN, so never commit it):
    work/mgb_analysis_clean.csv

Usage:
    python src/mgb/build_mgb_analysis_dataset.py
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

# psychiatric ICD prefixes (depression/anxiety/substance + the rest), for deriving
# a post-op point-prevalence flag from free-text-ish ICD columns.
PSYCH_PREFIXES = ("F32", "F33", "F34", "F40", "F41", "F43", "F42", "F31",
                  "F10", "F11", "F12", "F13", "F14", "F15", "F16", "F17", "F18", "F19",
                  "F20", "F25", "F90", "F06")


def parse_score(x) -> float:
    if pd.isna(x):
        return np.nan
    s = str(x).strip().replace("[", "").replace("]", "")
    m = re.search(r"-?\d+\.?\d*", s)
    return float(m.group()) if m else np.nan


def has_psych_code(row_vals) -> int:
    for v in row_vals:
        if pd.isna(v):
            continue
        code = str(v).upper().replace(".", "").strip()
        if any(code.startswith(p) for p in PSYCH_PREFIXES):
            return 1
    return 0


def main() -> int:
    if not MERGED.exists() or not ROHAN.exists():
        sys.exit("Source MGB files not found; this runs on the institutional extract only.")

    m = pd.read_csv(MERGED, dtype=str)
    r = pd.read_excel(ROHAN, sheet_name="ASM analysis", dtype=str)
    # one row per patient: drop blank MRNs and de-duplicate (keep first)
    m = m[m["MRN"].notna()].drop_duplicates(subset="MRN", keep="first").copy()
    r = r[r["MRN"].notna()].drop_duplicates(subset="MRN", keep="first").copy()

    # --- re-parse PHQ-9 / GAD-7 from the source sheet (bracket-aware) ----------
    phq = pd.DataFrame({"MRN": r["MRN"]})
    phq["phq9_baseline"] = r["Baseline PHQ-9"].map(parse_score)
    phq["phq9_followup"] = r["PHQ-9.1"].map(parse_score)   # most complete follow-up column
    phq["phq9_mid"] = r["PHQ-9"].map(parse_score)
    phq["gad7_baseline"] = r["GAD-7"].map(parse_score)
    phq["gad7_followup"] = r["GAD-7.2"].map(parse_score)
    phq["gad7_mid"] = r["GAD-7.1"].map(parse_score)

    # Pre/post used for the symptom analyses: the last column is the last follow-up,
    # and the two earlier columns are coalesced into a single baseline (earliest
    # value preferred, filled from the other) to maximize paired coverage.
    phq["phq9_pre"] = phq["phq9_baseline"].fillna(phq["phq9_mid"])
    phq["phq9_post"] = phq["phq9_followup"]
    phq["gad7_pre"] = phq["gad7_baseline"].fillna(phq["gad7_mid"])
    phq["gad7_post"] = phq["gad7_followup"]

    df = m.merge(phq, on="MRN", how="left")

    # --- post-op point-prevalence psychiatric flag from follow-up ICD columns --
    postop_icd_cols = [c for c in df.columns if "Post-op last follow" in c]
    df["postop_psych_pointprev"] = df[postop_icd_cols].apply(lambda row: has_psych_code(row.values), axis=1)

    # --- multiple-procedure flag (prior monitoring + resection, or staged ops) -
    def yn(col):
        return pd.to_numeric(df[col], errors="coerce").fillna(0) if col in df.columns else 0
    prior_mon = yn("Prior invasive monitoring? 0=no, 1= yes")
    prior_res = yn("Prior resective intervention? 0=no, 1= yes")
    prior_oth = yn("Prior other interventions? 0=no, 1= yes")
    df["multiple_procedure"] = ((prior_mon + prior_res + prior_oth) > 0).astype(int)

    # --- tidy covariates -------------------------------------------------------
    df["seizure_free"] = (df["Seizure-free at last follow-up?"].astype(str).str.strip().str.lower() == "y").astype(int)
    df["age"] = pd.to_numeric(df["age_at_surgery"], errors="coerce")
    df["female_n"] = pd.to_numeric(df["female"], errors="coerce")
    df["svi"] = pd.to_numeric(df["SVI_overall"], errors="coerce")
    df["followup_years"] = pd.to_numeric(df.get("Length of follow-up "), errors="coerce")
    for c in ["preop_any_psych_dx", "postop_any_psych_dx", "preop_depression", "postop_depression",
              "preop_anxiety", "postop_anxiety"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df.to_csv(OUT / "mgb_analysis_clean.csv", index=False)
    print(f"Wrote {OUT / 'mgb_analysis_clean.csv'}  rows={len(df)}")
    print("preop_any_psych_dx:", int(df['preop_any_psych_dx'].sum()),
          "| postop cumulative:", int(df['postop_any_psych_dx'].sum()),
          "| postop point-prevalence:", int(df['postop_psych_pointprev'].sum()),
          "| multiple_procedure:", int(df['multiple_procedure'].sum()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
