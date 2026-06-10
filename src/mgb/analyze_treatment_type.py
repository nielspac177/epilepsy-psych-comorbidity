#!/usr/bin/env python3
"""
Adam's question: does TREATMENT TYPE predict postoperative psychiatric
improvement in the MGB cohort, beyond the factors already in the model?

Outcome: `improved` (manuscript a-priori composite = net decrease in psychiatric
diagnoses OR PHQ-9 drop >= 5 OR GAD-7 drop >= 4).
Predictor of interest: treatment_group (RES_ABLATIVE [resection/LITT] vs NEUROMOD
[RNS/DBS/VNS]); NONE reported separately, never pooled.

Reproducible: reads work/mgb_clean_review.csv (built by build_clean_mgb_dataset.py),
writes work/treatment_type_results.json and prints an APA-style report.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.power import NormalIndPower

DATA = Path(__file__).resolve().parents[2] / "work" / "mgb_clean_review.csv"
OUT = DATA.parent / "treatment_type_results.json"


def fisher_2x2(df, group_col, groups, outcome):
    sub = df[df[group_col].isin(groups)]
    tab = pd.crosstab(sub[group_col], sub[outcome]).reindex(index=groups, columns=[0, 1]).fillna(0)
    a, b = tab.loc[groups[0], 1], tab.loc[groups[0], 0]  # ref: events, non-events
    c, d = tab.loc[groups[1], 1], tab.loc[groups[1], 0]
    odds, p = stats.fisher_exact([[c, d], [a, b]])  # OR = groups[1] vs groups[0]
    # Haldane-corrected OR + CI
    a_, b_, c_, d_ = a + .5, b + .5, c + .5, d + .5
    or_h = (c_ * b_) / (d_ * a_)
    se = np.sqrt(1/a_ + 1/b_ + 1/c_ + 1/d_)
    lo, hi = np.exp(np.log(or_h) - 1.96*se), np.exp(np.log(or_h) + 1.96*se)
    # Cramer's V
    chi2 = stats.chi2_contingency(tab.values + 0)[0]
    nobs = tab.values.sum()
    v = np.sqrt(chi2 / nobs)
    return {
        "n": int(nobs),
        f"{groups[0]}_rate": f"{int(tab.loc[groups[0],1])}/{int(tab.loc[groups[0]].sum())} = {100*tab.loc[groups[0],1]/tab.loc[groups[0]].sum():.1f}%",
        f"{groups[1]}_rate": f"{int(tab.loc[groups[1],1])}/{int(tab.loc[groups[1]].sum())} = {100*tab.loc[groups[1],1]/tab.loc[groups[1]].sum():.1f}%",
        "OR_neuromod_vs_resablative": round(or_h, 2),
        "OR_CI": [round(lo, 2), round(hi, 2)],
        "fisher_p": round(p, 4),
        "cramers_v": round(v, 3),
    }


def main():
    df = pd.read_csv(DATA)
    out = {}

    # ---------- 1. Descriptives ----------
    out["overall_improved"] = f"{df['improved'].sum()}/{len(df)} = {100*df['improved'].mean():.1f}%"
    out["by_group"] = (
        df.groupby("treatment_group")["improved"].agg(["sum", "count", "mean"]).assign(
            pct=lambda d: (100*d["mean"]).round(1)).to_dict("index"))

    # ---------- 2. Bivariate (composite) ----------
    out["bivariate_composite"] = fisher_2x2(df, "treatment_group",
                                            ["RES_ABLATIVE", "NEUROMOD"], "improved")
    # 5-category chi-square
    sub5 = df.dropna(subset=["treatment_type"])
    tab5 = pd.crosstab(sub5["treatment_type"], sub5["improved"])
    chi2, p5, _, _ = stats.chi2_contingency(tab5)
    out["fivecat_chi2"] = {"chi2": round(chi2, 2), "p": round(p5, 3),
                           "note": "expected counts very small; unreliable",
                           "table": tab5.to_dict("index")}

    # ---------- 3. Bivariate by component ----------
    out["bivariate_components"] = {}
    for comp, col in [("symptom_PHQ", "imp_phq"), ("symptom_GAD", "imp_gad"), ("dx_decrease", "imp_dx")]:
        d2 = df.dropna(subset=[col])
        d2 = d2.assign(_o=d2[col].astype(int))
        try:
            out["bivariate_components"][comp] = fisher_2x2(d2, "treatment_group",
                                                           ["RES_ABLATIVE", "NEUROMOD"], "_o")
        except Exception as e:
            out["bivariate_components"][comp] = {"error": str(e)}

    # ---------- 4. Confounding by indication: seizure freedom by group ----------
    out["confounding_seizure_free"] = fisher_2x2(df, "treatment_group",
                                                 ["RES_ABLATIVE", "NEUROMOD"], "seizure_free")

    # ---------- 5. Multivariable logistic ----------
    model_df = df[df["treatment_group"].isin(["RES_ABLATIVE", "NEUROMOD"])].copy()
    model_df["neuromod"] = (model_df["treatment_group"] == "NEUROMOD").astype(int)
    model_df["svi10"] = model_df["svi_overall"] * 10  # per 0.1-unit
    covars = ["seizure_free", "svi10", "insurance_public", "age_at_surgery", "female"]
    fit_df = model_df.dropna(subset=["improved", "neuromod"] + covars)
    events = int(fit_df["improved"].sum())
    out["multivariable"] = {"n": int(len(fit_df)), "events": events,
                            "epv_with_treatment": round(events / (len(covars) + 1), 2)}
    try:
        m_full = smf.logit("improved ~ neuromod + seizure_free + svi10 + insurance_public + age_at_surgery + female",
                           data=fit_df).fit(disp=0)
        m_base = smf.logit("improved ~ seizure_free + svi10 + insurance_public + age_at_surgery + female",
                           data=fit_df).fit(disp=0)
        def orrow(m, term):
            return {"OR": round(np.exp(m.params[term]), 2),
                    "CI": [round(np.exp(m.conf_int().loc[term, 0]), 2),
                           round(np.exp(m.conf_int().loc[term, 1]), 2)],
                    "p": round(m.pvalues[term], 3)}
        out["multivariable"]["treatment_OR_neuromod_vs_resablative"] = orrow(m_full, "neuromod")
        out["multivariable"]["seizure_free_OR_with_treatment"] = orrow(m_full, "seizure_free")
        out["multivariable"]["seizure_free_OR_base_model"] = orrow(m_base, "seizure_free")
    except Exception as e:
        out["multivariable"]["error"] = str(e)

    # ---------- 6. Sensitivity: detectable effect ----------
    p_ref = df.loc[df.treatment_group == "RES_ABLATIVE", "improved"].mean()
    n_neuromod = int((df.treatment_group == "NEUROMOD").sum())
    n_ref = int((df.treatment_group == "RES_ABLATIVE").sum())
    analysis = NormalIndPower()
    # minimum detectable difference in proportions at 80% power
    try:
        from statsmodels.stats.proportion import proportion_effectsize
        # solve for p2 giving power 0.8 (search)
        grid = np.linspace(p_ref, 0.8, 200)
        det = None
        for p2 in grid:
            es = proportion_effectsize(p2, p_ref)
            pw = analysis.power(effect_size=es, nobs1=n_neuromod, ratio=n_ref/n_neuromod, alpha=0.05)
            if pw >= 0.8:
                det = round(p2, 3); break
        out["sensitivity"] = {"resablative_rate": round(float(p_ref), 3),
                              "n_neuromod": n_neuromod, "n_resablative": n_ref,
                              "min_detectable_neuromod_rate_80pct": det,
                              "interpretation": (f"With these n, 80% power only to detect a NEUROMOD "
                                                 f"improvement rate >= {det} vs {p_ref:.1%} (a large gap).")}
    except Exception as e:
        out["sensitivity"] = {"error": str(e)}

    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
