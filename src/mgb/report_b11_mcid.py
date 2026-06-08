#!/usr/bin/env python3
"""
Reviewer comment B11 (Glaser): percentage of patients with a clinically
meaningful improvement in PHQ-9 and GAD-7 after epilepsy surgery.

Clinically meaningful improvement is defined two ways:
  PRIMARY  = ED50 minimal clinically important difference (MCID) from
             Bauer-Staeb et al. 2021 (BJPsych Open):
               PHQ-9 drop >= 3.7 points
               GAD-7 drop >= 3.3 points
  SENSITIVITY = conventional fixed-point reliable-change thresholds:
               PHQ-9 drop >= 5 points
               GAD-7 drop >= 4 points

Improvement = (pre - post) >= threshold  (a DROP in score = clinical improvement).

Pairings:
  PHQ-9 primary : phq9_baseline -> phq9_followup
  PHQ-9 alt     : phq9_mid      -> phq9_followup   (larger n)
  GAD-7 primary : gad7_baseline -> gad7_followup
  GAD-7 alt     : gad7_mid      -> gad7_followup   (larger n)

Reference:
  Bauer-Staeb C, Kounali D-Z, Welton NJ, et al. Effective dose 50 method as the
  minimal clinically important difference: Evidence from depression and anxiety
  trials. BJPsych Open. 2021. (ED50 MCID: PHQ-9 ~3.7, GAD-7 ~3.3.)

DATA CAVEAT (state in every output):
  This is the currently-available extract. It reproduces the manuscript's PRE-OP
  psychiatric prevalence (~49-51%) but NOT the manuscript's reported POST-OP
  decrease (Table 3: 49.1% -> 42.5%); here post-op prevalence is stable-to-higher.
  The paired PHQ-9 / GAD-7 n here is far below the manuscript's reported 116 / 112.
  Treat ALL numbers below as PROVISIONAL pending the verified Table-3 extract.
  This code is designed to run unchanged on that corrected extract.
"""

import os
import pandas as pd
import numpy as np
from scipy.stats import wilcoxon

DATA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "work", "mgb_analysis_clean.csv",
)

THRESHOLDS = {
    "PHQ-9": {"ed50": 3.7, "fixed": 5.0},
    "GAD-7": {"ed50": 3.3, "fixed": 4.0},
}

CAVEAT = (
    "PROVISIONAL: currently-available extract. Reproduces pre-op psychiatric "
    "prevalence (~49-51%) but not the manuscript's post-op decrease (Table 3 "
    "49.1%->42.5%); post-op prevalence here is stable-to-higher. Paired PHQ-9/"
    "GAD-7 n is far below the manuscript's 116/112. Numbers are provisional "
    "pending the verified Table-3 extract."
)


def analyze(df, instrument, pre_col, post_col, label):
    ed50 = THRESHOLDS[instrument]["ed50"]
    fixed = THRESHOLDS[instrument]["fixed"]
    paired = df[[pre_col, post_col]].dropna()
    n = len(paired)
    pre = paired[pre_col].to_numpy(dtype=float)
    post = paired[post_col].to_numpy(dtype=float)
    drop = pre - post  # positive = improvement
    change = post - pre  # signed change (negative = improvement)

    res = {
        "instrument": instrument,
        "pairing": label,
        "pre_col": pre_col,
        "post_col": post_col,
        "n_paired": n,
        "ed50_threshold": ed50,
        "fixed_threshold": fixed,
    }
    if n == 0:
        res.update({
            "n_improved_ed50": 0, "pct_improved_ed50": float("nan"),
            "n_improved_fixed": 0, "pct_improved_fixed": float("nan"),
            "median_change": float("nan"), "median_drop": float("nan"),
            "wilcoxon_p": float("nan"),
        })
        return res

    n_ed50 = int(np.sum(drop >= ed50))
    n_fixed = int(np.sum(drop >= fixed))
    res["n_improved_ed50"] = n_ed50
    res["pct_improved_ed50"] = 100.0 * n_ed50 / n
    res["n_improved_fixed"] = n_fixed
    res["pct_improved_fixed"] = 100.0 * n_fixed / n
    res["median_change"] = float(np.median(change))  # signed (post-pre)
    res["median_drop"] = float(np.median(drop))

    # Wilcoxon signed-rank on paired pre vs post
    if n >= 1 and np.any(drop != 0):
        try:
            res["wilcoxon_p"] = float(wilcoxon(pre, post, zero_method="wilcox").pvalue)
        except ValueError:
            res["wilcoxon_p"] = float("nan")
    else:
        res["wilcoxon_p"] = float("nan")
    return res


def main():
    df = pd.read_csv(DATA)
    runs = [
        analyze(df, "PHQ-9", "phq9_baseline", "phq9_followup", "primary (baseline->follow-up)"),
        analyze(df, "PHQ-9", "phq9_mid", "phq9_followup", "alternate (mid->follow-up)"),
        analyze(df, "GAD-7", "gad7_baseline", "gad7_followup", "primary (baseline->follow-up)"),
        analyze(df, "GAD-7", "gad7_mid", "gad7_followup", "alternate (mid->follow-up)"),
    ]
    out = pd.DataFrame(runs)

    print("=" * 78)
    print("B11 (Glaser): Clinically meaningful improvement in PHQ-9 / GAD-7 post-surgery")
    print("ED50 MCID thresholds from Bauer-Staeb et al. 2021 (PHQ-9>=3.7, GAD-7>=3.3)")
    print("=" * 78)
    cols = ["instrument", "pairing", "n_paired",
            "n_improved_ed50", "pct_improved_ed50",
            "n_improved_fixed", "pct_improved_fixed",
            "median_change", "wilcoxon_p"]
    with pd.option_context("display.width", 200, "display.max_columns", None):
        print(out[cols].to_string(index=False))
    print()
    print("DATA CAVEAT:", CAVEAT)
    return out


if __name__ == "__main__":
    main()
