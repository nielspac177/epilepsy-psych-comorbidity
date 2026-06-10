#!/usr/bin/env python3
"""
Simple mediation: does seizure freedom mediate the effect of treatment
(type and number) on postoperative psychiatric improvement?

Causal structure (per A. Glaser):
    treatment  --a-->  seizure freedom  --b-->  psychiatric improvement
    treatment  ------------ direct (c') ----------------^
    total effect c = direct c' + indirect (a*b)

We report, for each exposure (treatment type = neuromodulation vs resective/
ablative; and number of treatments):
  - DESCRIPTIVE seizure-freedom counts/percent by exposure level,
  - SIMPLE logistic regressions for each path,
  - the indirect (a*b) and direct (c') effects on the log-odds scale with
    nonparametric bootstrap 95% CIs and the proportion mediated.

Reads work/mgb_clean_review.csv; writes work/mediation_results.json.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

DATA = Path(__file__).resolve().parents[2] / "work" / "mgb_clean_review.csv"
OUT = DATA.parent / "mediation_results.json"
RNG = np.random.default_rng(20260610)
N_BOOT = 2000


def logit_coef(formula, data, term):
    m = smf.logit(formula, data=data).fit(disp=0)
    return float(m.params[term]), float(m.pvalues[term]), \
        [float(np.exp(m.conf_int().loc[term, 0])), float(np.exp(m.conf_int().loc[term, 1]))]


def mediation(df, exposure, mediator="seizure_free", outcome="improved"):
    d = df.dropna(subset=[exposure, mediator, outcome]).copy()
    fa = f"{mediator} ~ {exposure}"
    fb = f"{outcome} ~ {mediator} + {exposure}"
    fc = f"{outcome} ~ {exposure}"
    fcp = f"{outcome} ~ {exposure} + {mediator}"

    a, ap, a_or = logit_coef(fa, d, exposure)
    # b path and direct from the same adjusted model
    mb = smf.logit(fb, d).fit(disp=0)
    b, bp = float(mb.params[mediator]), float(mb.pvalues[mediator])
    cprime, cpp = float(mb.params[exposure]), float(mb.pvalues[exposure])
    c, cp, _ = logit_coef(fc, d, exposure)
    indirect = a * b
    total = c
    prop_med = indirect / total if abs(total) > 1e-6 else np.nan

    # bootstrap indirect a*b
    boot = []
    n = len(d)
    for _ in range(N_BOOT):
        s = d.iloc[RNG.integers(0, n, n)]
        try:
            ai = smf.logit(fa, s).fit(disp=0).params[exposure]
            bi = smf.logit(fb, s).fit(disp=0).params[mediator]
            boot.append(ai * bi)
        except Exception:
            continue
    boot = np.array(boot)
    ci = [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))] if len(boot) > 100 else [np.nan, np.nan]

    return {
        "exposure": exposure, "n": int(n), "events_outcome": int(d[outcome].sum()),
        "a_path_exposure_to_seizurefree": {"log_odds": round(a, 3), "OR": round(np.exp(a), 2),
                                           "OR_CI": [round(x, 2) for x in a_or], "p": round(ap, 4)},
        "b_path_seizurefree_to_improve": {"log_odds": round(b, 3), "OR": round(np.exp(b), 2), "p": round(bp, 3)},
        "c_total_exposure_to_improve": {"log_odds": round(c, 3), "OR": round(np.exp(c), 2), "p": round(cp, 3)},
        "cprime_direct_adjusted": {"log_odds": round(cprime, 3), "OR": round(np.exp(cprime), 2), "p": round(cpp, 3)},
        "indirect_a_times_b": {"log_odds": round(indirect, 4), "boot95CI": [round(x, 4) for x in ci]},
        "proportion_mediated": round(float(prop_med), 3) if np.isfinite(prop_med) else None,
    }


def descriptive(df, by, label):
    rows = {}
    g = df.dropna(subset=[by]).groupby(by)
    for k, sub in g:
        sf = sub["seizure_free"]
        rows[str(k)] = {"n": int(len(sub)), "seizure_free_n": int(sf.sum()),
                        "seizure_free_pct": round(100 * sf.mean(), 1),
                        "improved_n": int(sub["improved"].sum()),
                        "improved_pct": round(100 * sub["improved"].mean(), 1)}
    return rows


def main():
    df = pd.read_csv(DATA)
    df["neuromod"] = np.where(df.treatment_group == "NEUROMOD", 1,
                              np.where(df.treatment_group == "RES_ABLATIVE", 0, np.nan))

    out = {}
    out["descriptive_by_treatment_type"] = descriptive(
        df[df.treatment_group.isin(["RES_ABLATIVE", "NEUROMOD", "NONE"])], "treatment_group", "treatment type")
    out["descriptive_by_n_treatments"] = descriptive(df, "n_treatments", "number of treatments")

    # a-path descriptive tests
    t = pd.crosstab(df.loc[df.neuromod.notna(), "neuromod"], df.loc[df.neuromod.notna(), "seizure_free"])
    out["seizurefree_by_treatment_fisher_p"] = round(stats.fisher_exact(t.values)[1], 5)
    # trend test seizure freedom across n_treatments
    sub = df.dropna(subset=["n_treatments", "seizure_free"])
    out["seizurefree_trend_over_ntreatments_logit"] = logit_coef(
        "seizure_free ~ n_treatments", sub, "n_treatments")

    out["mediation_treatment_type"] = mediation(df[df.neuromod.notna()], "neuromod")
    out["mediation_n_treatments"] = mediation(df, "n_treatments")

    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
