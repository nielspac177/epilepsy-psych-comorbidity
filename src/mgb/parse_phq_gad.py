#!/usr/bin/env python3
"""
Canonical, bracket-aware parser + paired-improvement analysis for the MGB
PHQ-9 / GAD-7 data.

WHY THIS EXISTS
The follow-up PHQ-9/GAD-7 scores in the source workbook are stored as TEXT in
bracket notation (e.g. "[6]", "[13]") and a few as "0 (Phq4score)". A naive
pandas.to_numeric() drops every bracketed value, which is how an earlier merge
(results/merged_deprivation_psych_data.csv) silently lost most follow-up scores.
This module parses them correctly and reports paired coverage under each
plausible pre/post column mapping, so the timepoint mapping is an explicit,
auditable choice rather than a hidden assumption.

DATA-PROVENANCE FLAG
Even with correct parsing, paired pre+post coverage in this workbook tops out
around n=45 (PHQ-9) / n=31 (GAD-7) -- well below the manuscript's Table 3 of
n=116 (PHQ-9) / n=112 (GAD-7). Table 3 therefore came from a larger extract not
present in this directory. Numbers produced here are PROVISIONAL until that
extract is supplied; this script is written to run unchanged on it.

MCID DEFINITIONS (clinically meaningful improvement, Glaser comment)
  PRIMARY  : ED50 average MCID, Bauer-Staeb et al. 2021 -> PHQ-9 drop >= 3.7,
             GAD-7 drop >= 3.3
  SENSITIVITY: fixed thresholds -> PHQ-9 drop >= 5, GAD-7 drop >= 4

Usage:
    python src/mgb/parse_phq_gad.py [path_to_workbook.xlsx] [sheet_name]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_XLSX = "/Users/nielspacheco/Desktop/Research/Rolston lab/Psych_epilepsy_surgery/Epilepsy_surgery_rohan_dataset_v1.xlsx"
DEFAULT_SHEET = "ASM analysis"
OUT = Path(__file__).resolve().parents[2] / "verification_out"
OUT.mkdir(exist_ok=True)

MCID = {  # (primary_ED50, sensitivity_fixed)
    "PHQ-9": (3.7, 5),
    "GAD-7": (3.3, 4),
}


def parse_score(x) -> float:
    """Extract the first numeric value from messy cells: '[6]', '0 (Phq4score)', 7.0, ''."""
    if pd.isna(x):
        return np.nan
    s = str(x).strip().replace("[", "").replace("]", "")
    m = re.search(r"-?\d+\.?\d*", s)
    return float(m.group()) if m else np.nan


def improvement_stats(pre: pd.Series, post: pd.Series, ed50: float, fixed: float) -> dict:
    mask = pre.notna() & post.notna()
    n = int(mask.sum())
    if n == 0:
        return {"n_paired": 0}
    drop = pre[mask] - post[mask]  # positive = improvement
    return {
        "n_paired": n,
        "median_pre": float(pre[mask].median()),
        "median_post": float(post[mask].median()),
        "median_change": float(drop.median()),
        "pct_improved_ED50_primary": round(100 * float((drop >= ed50).mean()), 1),
        "n_improved_ED50_primary": int((drop >= ed50).sum()),
        "pct_improved_fixed_sensitivity": round(100 * float((drop >= fixed).mean()), 1),
        "n_improved_fixed_sensitivity": int((drop >= fixed).sum()),
    }


def main() -> int:
    xlsx = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_XLSX
    sheet = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_SHEET
    df = pd.read_excel(xlsx, sheet_name=sheet, dtype=str)

    cols = ["Baseline PHQ-9", "PHQ-9", "PHQ-9.1", "GAD-7", "GAD-7.1", "GAD-7.2"]
    P = {c: df[c].map(parse_score) for c in cols if c in df.columns}
    coverage = {c: int(s.notna().sum()) for c, s in P.items()}

    # Report every plausible pre/post mapping so the choice is explicit.
    phq_maps = [("Baseline PHQ-9", "PHQ-9"), ("Baseline PHQ-9", "PHQ-9.1"), ("PHQ-9", "PHQ-9.1")]
    gad_maps = [("GAD-7", "GAD-7.1"), ("GAD-7", "GAD-7.2"), ("GAD-7.1", "GAD-7.2")]

    result = {"source": f"{Path(xlsx).name} :: {sheet}", "single_timepoint_coverage": coverage,
              "PHQ-9_mappings": {}, "GAD-7_mappings": {}}
    for pre, post in phq_maps:
        if pre in P and post in P:
            result["PHQ-9_mappings"][f"{pre} -> {post}"] = improvement_stats(P[pre], P[post], *MCID["PHQ-9"])
    for pre, post in gad_maps:
        if pre in P and post in P:
            result["GAD-7_mappings"][f"{pre} -> {post}"] = improvement_stats(P[pre], P[post], *MCID["GAD-7"])

    result["PROVENANCE_FLAG"] = (
        "PROVISIONAL: max paired n here is far below manuscript Table 3 (PHQ-9 116 / "
        "GAD-7 112). Table 3 used a larger extract not in this directory. Re-run this "
        "script on that extract for reportable numbers. Timepoint mapping must be "
        "confirmed by the data owner."
    )
    (OUT / "mgb_phq_gad_improvement.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
