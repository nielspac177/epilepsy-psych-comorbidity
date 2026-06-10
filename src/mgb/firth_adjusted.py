#!/usr/bin/env python3
"""
Adjusted treatment-type analysis with Firth penalized logistic regression.

Firth's method (penalized likelihood with the Jeffreys-prior term 0.5*log|I(beta)|)
removes small-sample bias and is the standard fix for the quasi-separation that
arises when seizure freedom is included (the neuromod & seizure-free cell has 0
events). firthlogist requires Python < 3.11, so Firth is implemented directly here
via Newton-Raphson with the modified score
    U*(beta)_j = sum_i [ y_i - pi_i + h_i*(0.5 - pi_i) ] x_ij,
where h_i are the diagonal hat-matrix elements. Wald confidence intervals from the
penalized information matrix are reported (a profile-likelihood interval would be
marginally wider; the inference is unchanged).

Models (treatment effect = neuromodulation vs resective/ablative):
  1. RECOMMENDED total effect: pre-treatment confounders only (NO seizure freedom,
     which is a mediator of treatment).
  2. SENSITIVITY: the published covariate set plus seizure freedom (separation present;
     Firth required).

Also reports an E-value (VanderWeele & Ding) for unmeasured confounding.
Reads work/mgb_clean_review.csv.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats
from pathlib import Path
import statsmodels.formula.api as smf

DATA = Path(__file__).resolve().parents[2] / "work" / "mgb_clean_review.csv"


def firth_logit(X, y, max_iter=200, tol=1e-8):
    """Firth penalized logistic regression. X includes an intercept column."""
    n, p = X.shape
    beta = np.zeros(p)
    for _ in range(max_iter):
        eta = X @ beta
        pi = 1.0 / (1.0 + np.exp(-eta))
        W = pi * (1.0 - pi)
        XtWX = X.T @ (W[:, None] * X)
        XtWX_inv = np.linalg.pinv(XtWX)
        Wsqrt = np.sqrt(W)
        Q = Wsqrt[:, None] * X
        h = np.einsum("ij,jk,ik->i", Q, XtWX_inv, Q)  # hat-matrix diagonal
        U = X.T @ (y - pi + h * (0.5 - pi))            # Firth-modified score
        step = XtWX_inv @ U
        beta = beta + step
        if np.max(np.abs(step)) < tol:
            break
    se = np.sqrt(np.diag(XtWX_inv))
    z = beta / se
    pval = 2 * (1 - stats.norm.cdf(np.abs(z)))
    return beta, se, pval


def run(df, covars, label):
    cols = ["neuromod"] + covars
    d = df.dropna(subset=cols + ["improved"]).copy()
    X = np.column_stack([np.ones(len(d))] + [d[c].astype(float).values for c in cols])
    y = d["improved"].astype(float).values
    # standard MLE for comparison
    try:
        m = smf.logit("improved ~ " + " + ".join(cols), d).fit(disp=0)
        mle = (np.exp(m.params["neuromod"]),
               np.exp(m.conf_int().loc["neuromod"]).tolist(), m.pvalues["neuromod"])
    except Exception as e:
        mle = ("sep/err: " + str(e)[:40], None, None)
    b, se, p = firth_logit(X, y)
    idx = 1  # neuromod is first after intercept
    OR = np.exp(b[idx]); lo = np.exp(b[idx] - 1.96 * se[idx]); hi = np.exp(b[idx] + 1.96 * se[idx])
    print(f"\n=== {label} ===")
    print(f"  covariates: neuromod + {', '.join(covars) if covars else '(none)'}")
    print(f"  n={len(d)}  events={int(y.sum())}  EPV={y.sum()/len(cols):.1f}")
    if mle[1]:
        print(f"  MLE   neuromod OR={mle[0]:.2f} ({mle[1][0]:.2f}-{mle[1][1]:.2f}) p={mle[2]:.3f}")
    else:
        print(f"  MLE   {mle[0]}")
    print(f"  FIRTH neuromod OR={OR:.2f} ({lo:.2f}-{hi:.2f}) p={p[idx]:.3f}")
    return OR, lo, hi


def evalue_or(or_point, lo, hi, baseline_risk):
    """E-value for an odds ratio with a common outcome (VanderWeele & Ding)."""
    def rr_from_or(o):
        # convert OR to approximate RR given baseline risk p0
        return o / (1 - baseline_risk + baseline_risk * o)
    def ev(rr):
        rr = rr if rr >= 1 else 1 / rr
        return rr + np.sqrt(rr * (rr - 1))
    rr = rr_from_or(or_point)
    # CI bound nearest the null
    rrs = [rr_from_or(lo), rr_from_or(hi)]
    if lo < 1 < hi:
        ci_ev = 1.0  # CI crosses null
    else:
        nearest = min(rrs, key=lambda r: abs(np.log(r)))
        ci_ev = ev(nearest)
    return round(ev(rr), 2), round(ci_ev, 2)


def main():
    df = pd.read_csv(DATA)
    d = df[df.treatment_group.isin(["RES_ABLATIVE", "NEUROMOD"])].copy()
    d["neuromod"] = (d.treatment_group == "NEUROMOD").astype(int)
    d["svi10"] = d.svi_overall * 10

    print("Treatment effect = neuromodulation vs resective/ablative; outcome = composite improvement")
    rec = run(d, ["preop_any_psych", "age_at_surgery", "female"],
              "RECOMMENDED total effect (pre-treatment confounders, NO seizure freedom)")
    run(d, ["seizure_free", "svi10", "insurance_public", "age_at_surgery", "female"],
        "SENSITIVITY: published covariates + seizure freedom (mediator; separation -> Firth)")

    base = d.improved.mean()
    ev_pt, ev_ci = evalue_or(rec[0], rec[1], rec[2], base)
    print(f"\n=== E-value (unmeasured confounding), recommended model ===")
    print(f"  baseline improvement risk={base:.3f}; E-value point={ev_pt}, E-value for CI={ev_ci}")
    print(f"  An unmeasured confounder would need a risk ratio of at least {ev_pt} with both")
    print(f"  treatment and outcome to move the point estimate to the null (and {ev_ci} for the CI).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
