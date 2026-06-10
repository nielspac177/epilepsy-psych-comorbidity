#!/usr/bin/env python3
"""
Causal-inference framing of Adam's question (senior-data-scientist Workflow 5).

Treatment assignment (neuromodulation vs resective/ablative) is OBSERVATIONAL and
confounded by indication. Before estimating any effect of treatment type on
psychiatric improvement, we must ask whether the groups are comparable. We:
  1. compute standardized mean differences (SMD) of PRE-treatment covariates,
  2. fit a propensity score (P[neuromod | pre-treatment covariates]) and check
     overlap / positivity (common support),
  3. report an IPTW-adjusted treatment effect, with explicit caveats.

Seizure freedom is POST-treatment (a consequence of modality choice), so it is the
mechanism of confounding, not a propensity covariate; it is excluded from the
propensity model and reported separately as the indication gradient.

Reads work/mgb_clean_review.csv; writes work/causal_treatment_type.json.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

DATA = Path(__file__).resolve().parents[2] / "work" / "mgb_clean_review.csv"
OUT = DATA.parent / "causal_treatment_type.json"

PRE_COVARS = ["age_at_surgery", "female", "svi_overall", "insurance_public",
              "epilepsy_duration", "preop_aeds", "preop_any_psych"]


def smd(a, b):
    """Standardized mean difference between two groups (|>0.1| = imbalance)."""
    ma, mb = np.nanmean(a), np.nanmean(b)
    sa, sb = np.nanvar(a, ddof=1), np.nanvar(b, ddof=1)
    pooled = np.sqrt((sa + sb) / 2)
    return (ma - mb) / pooled if pooled > 0 else np.nan


def main():
    df = pd.read_csv(DATA)
    d = df[df.treatment_group.isin(["RES_ABLATIVE", "NEUROMOD"])].copy()
    d["neuromod"] = (d.treatment_group == "NEUROMOD").astype(int)

    out = {"n_resablative": int((d.neuromod == 0).sum()),
           "n_neuromod": int((d.neuromod == 1).sum())}

    # ---- 1. covariate balance (SMD) ----------------------------------------
    bal = {}
    for c in PRE_COVARS:
        nm = d.loc[d.neuromod == 1, c]
        rs = d.loc[d.neuromod == 0, c]
        bal[c] = {"neuromod_mean": round(float(np.nanmean(nm)), 3),
                  "resablative_mean": round(float(np.nanmean(rs)), 3),
                  "SMD": round(float(smd(nm, rs)), 3)}
    out["covariate_balance_SMD"] = bal
    out["n_covars_imbalanced_SMD_gt_0.1"] = int(sum(abs(v["SMD"]) > 0.1 for v in bal.values()))

    # ---- 2. propensity score + overlap / positivity ------------------------
    fit = d.dropna(subset=PRE_COVARS + ["neuromod"]).copy()
    ps_model = smf.logit("neuromod ~ age_at_surgery + female + svi_overall + "
                         "insurance_public + epilepsy_duration + preop_aeds + preop_any_psych",
                         data=fit).fit(disp=0)
    fit["ps"] = ps_model.predict(fit)
    ps_nm = fit.loc[fit.neuromod == 1, "ps"]
    ps_rs = fit.loc[fit.neuromod == 0, "ps"]
    # common support = overlap of the two propensity ranges
    lo = max(ps_nm.min(), ps_rs.min())
    hi = min(ps_nm.max(), ps_rs.max())
    in_support = fit[(fit.ps >= lo) & (fit.ps <= hi)]
    out["propensity"] = {
        "neuromod_ps_range": [round(float(ps_nm.min()), 3), round(float(ps_nm.max()), 3)],
        "resablative_ps_range": [round(float(ps_rs.min()), 3), round(float(ps_rs.max()), 3)],
        "common_support": [round(float(lo), 3), round(float(hi), 3)],
        "pct_in_common_support": round(100 * len(in_support) / len(fit), 1),
        "neuromod_outside_support": int((ps_nm > hi).sum() + (ps_nm < lo).sum()),
        "pseudo_r2": round(float(ps_model.prsquared), 3),
    }

    # ---- 3. IPTW-adjusted treatment effect on improvement ------------------
    fit["w"] = np.where(fit.neuromod == 1, 1/fit.ps, 1/(1-fit.ps))
    # stabilized weights
    p_treat = fit.neuromod.mean()
    fit["sw"] = np.where(fit.neuromod == 1, p_treat/fit.ps, (1-p_treat)/(1-fit.ps))
    out["iptw"] = {"max_stabilized_weight": round(float(fit.sw.max()), 2),
                   "mean_stabilized_weight": round(float(fit.sw.mean()), 2)}
    try:
        m = smf.glm("improved ~ neuromod", data=fit, freq_weights=fit.sw,
                    family=__import__("statsmodels.api", fromlist=["families"]).families.Binomial()).fit()
        out["iptw"]["treatment_OR_neuromod_vs_resablative"] = round(float(np.exp(m.params["neuromod"])), 2)
        ci = m.conf_int().loc["neuromod"]
        out["iptw"]["OR_CI"] = [round(float(np.exp(ci[0])), 2), round(float(np.exp(ci[1])), 2)]
        out["iptw"]["p"] = round(float(m.pvalues["neuromod"]), 3)
        out["iptw"]["caveat"] = ("IPTW point estimate only; with 33 events and unstable weights "
                                 "the CI is not trustworthy. Reported for completeness.")
    except Exception as e:
        out["iptw"]["error"] = str(e)

    out["method_note"] = (
        "Treatment type is observational and confounded by indication, so this script reports "
        "covariate balance (SMD), propensity overlap/positivity, and an IPTW-adjusted estimate as "
        "diagnostics. Interpret the estimand in light of the seizure-freedom gradient between groups "
        "and the available event count; see the analysis report for context.")

    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
