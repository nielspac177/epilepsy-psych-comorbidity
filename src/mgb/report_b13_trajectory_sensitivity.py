#!/usr/bin/env python3
"""
Reviewer comment B13 (Glaser) — postoperative psychiatric-trajectory sensitivity analysis.

The reviewer objects that the multiple-procedure sensitivity analysis is confusing
because excluding re-operated patients also excludes harder-to-treat / less
seizure-free patients, so the exclusion is NOT outcome-neutral.

This script:
  (1) Tests ANY psychiatric disorder preop -> postop for ALL patients, using two
      postop definitions: (a) point-prevalence (postop_psych_pointprev), the primary,
      and (b) cumulative-ever (postop_any_psych_dx). McNemar paired test.
  (2) Repeats EXCLUDING multiple_procedure==1, quantifying how much the exclusion
      shifts the estimate (the reviewer's core question).
  (3) Stratifies the trajectory by seizure_free (1 vs 0).
  (4) Depression and anxiety subscales separately, all-patients and excl-multi-proc.
  (5) Compares multiple_procedure==1 vs ==0 characteristics (seizure-free rate,
      preop psych burden) to show WHY exclusion is not neutral.

IMPORTANT DATA CAVEAT (state in every output):
  This is the currently-available extract. It reproduces the manuscript's PREOP
  psychiatric prevalence (~49-51%) but NOT the manuscript's reported POSTOP decrease
  (Table 3: 49.1% -> 42.5%); here postop prevalence is STABLE-TO-HIGHER. Paired
  PHQ-9/GAD-7 n is far below the manuscript's 116/112. All numbers are PROVISIONAL
  pending the verified Table-3 extract. The code runs unchanged on it.
"""

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, fisher_exact
from statsmodels.stats.contingency_tables import mcnemar

CSV = ("/Users/nielspacheco/Desktop/Research/Rolston lab/Psych_epilepsy_surgery/"
       "repro_build/epilepsy-psych-comorbidity/work/mgb_analysis_clean.csv")

CAVEAT = (
    "DATA CAVEAT: currently-available extract. Reproduces manuscript PREOP prevalence "
    "(~49-51%) but NOT the manuscript's reported POSTOP decrease (Table 3 49.1%->42.5%); "
    "here postop prevalence is stable-to-higher. Paired PHQ-9/GAD-7 n far below "
    "manuscript's 116/112. All numbers PROVISIONAL pending verified Table-3 extract."
)


def mcnemar_paired(df, pre_col, post_col, label):
    """Paired pre/post McNemar on a binary flag. Both columns must be 0/1, complete."""
    sub = df[[pre_col, post_col]].dropna()
    n = len(sub)
    pre = sub[pre_col].astype(int)
    post = sub[post_col].astype(int)
    # 2x2 discordance table
    a = int(((pre == 0) & (post == 0)).sum())  # neither
    b = int(((pre == 0) & (post == 1)).sum())  # new onset (0->1)
    c = int(((pre == 1) & (post == 0)).sum())  # remission (1->0)
    d = int(((pre == 1) & (post == 1)).sum())  # persistent
    table = [[a, b], [c, d]]
    discordant = b + c
    # exact binomial McNemar when discordant cells are small, else asymptotic w/ correction
    use_exact = discordant < 25
    res = mcnemar(table, exact=use_exact, correction=not use_exact)
    pre_prev = pre.mean()
    post_prev = post.mean()
    return {
        "label": label,
        "n": n,
        "pre_n": int(pre.sum()),
        "post_n": int(post.sum()),
        "pre_prev": pre_prev,
        "post_prev": post_prev,
        "delta_pp": (post_prev - pre_prev) * 100,
        "neither": a,
        "new_onset_0to1": b,
        "remission_1to0": c,
        "persistent": d,
        "discordant": discordant,
        "stat": float(res.statistic),
        "p": float(res.pvalue),
        "test": "exact" if use_exact else "asymptotic(cc)",
    }


def fmt_traj(r):
    return (f"{r['label']}: n={r['n']} | preop {r['pre_n']}/{r['n']} "
            f"({r['pre_prev']*100:.1f}%) -> postop {r['post_n']}/{r['n']} "
            f"({r['post_prev']*100:.1f}%) | delta {r['delta_pp']:+.1f}pp | "
            f"new-onset(0->1)={r['new_onset_0to1']}, remission(1->0)={r['remission_1to0']} | "
            f"McNemar {r['test']} stat={r['stat']:.3f}, p={r['p']:.4f}")


def chisq_2x2(df, group_col, outcome_col):
    """Group comparison: outcome rate by binary group. Returns rates + chi2/Fisher."""
    sub = df[[group_col, outcome_col]].dropna()
    ct = pd.crosstab(sub[group_col], sub[outcome_col])
    # ensure both outcome columns present
    for v in [0, 1]:
        if v not in ct.columns:
            ct[v] = 0
    ct = ct[[0, 1]]
    chi2, p_chi, dof, exp = chi2_contingency(ct, correction=True)
    # Fisher as backup for small expected counts
    p_fisher = None
    if (exp < 5).any():
        try:
            _, p_fisher = fisher_exact(ct.values)
        except Exception:
            p_fisher = None
    rate1 = ct.loc[1, 1] / ct.loc[1].sum() if 1 in ct.index else np.nan
    rate0 = ct.loc[0, 1] / ct.loc[0].sum() if 0 in ct.index else np.nan
    return {
        "rate_group1": rate1, "rate_group0": rate0,
        "n_group1": int(ct.loc[1].sum()) if 1 in ct.index else 0,
        "n_group0": int(ct.loc[0].sum()) if 0 in ct.index else 0,
        "chi2": chi2, "p_chi2": p_chi, "p_fisher": p_fisher,
        "small_expected": bool((exp < 5).any()),
    }


def main():
    df = pd.read_csv(CSV)
    N = len(df)
    print("=" * 100)
    print("B13 POSTOPERATIVE PSYCHIATRIC-TRAJECTORY SENSITIVITY ANALYSIS (Glaser)")
    print(f"N = {N} unique patients")
    print(CAVEAT)
    print("=" * 100)

    excl = int((df["multiple_procedure"] == 1).sum())
    keep = int((df["multiple_procedure"] == 0).sum())
    print(f"\nmultiple_procedure==1 (re-operated / prior intervention): {excl}")
    print(f"multiple_procedure==0 (single procedure, RETAINED in sensitivity): {keep}")

    df_single = df[df["multiple_procedure"] == 0].copy()

    # -------- (1)+(2) ANY psychiatric, two definitions, all vs excl-multi-proc -----
    print("\n" + "-" * 100)
    print("(1)/(2) ANY PSYCHIATRIC DISORDER: preop -> postop, two postop definitions")
    print("-" * 100)
    rows_traj = []
    for post_col, deftag in [("postop_psych_pointprev", "POINT-PREV (primary)"),
                             ("postop_any_psych_dx", "CUMULATIVE-ever")]:
        all_r = mcnemar_paired(df, "preop_any_psych_dx", post_col, f"ALL [{deftag}]")
        sng_r = mcnemar_paired(df_single, "preop_any_psych_dx", post_col,
                               f"EXCL multi-proc [{deftag}]")
        rows_traj += [all_r, sng_r]
        print("\n  " + fmt_traj(all_r))
        print("  " + fmt_traj(sng_r))
        shift = sng_r["delta_pp"] - all_r["delta_pp"]
        print(f"    --> Excluding {excl} multi-proc patients shifts the postop delta by "
              f"{shift:+.1f}pp (all={all_r['delta_pp']:+.1f}pp vs single={sng_r['delta_pp']:+.1f}pp); "
              f"postop prev {all_r['post_prev']*100:.1f}% -> {sng_r['post_prev']*100:.1f}%.")

    # -------- (3) Stratify by seizure_free --------------------------------------
    print("\n" + "-" * 100)
    print("(3) TRAJECTORY STRATIFIED BY SEIZURE FREEDOM (point-prevalence definition)")
    print("-" * 100)
    rows_sz = []
    for sz, name in [(1, "Seizure-FREE"), (0, "NOT seizure-free")]:
        sub = df[df["seizure_free"] == sz]
        r = mcnemar_paired(sub, "preop_any_psych_dx", "postop_psych_pointprev", name)
        rows_sz.append(r)
        print("\n  " + fmt_traj(r))
    # also cumulative for completeness
    print("\n  [cumulative-ever definition]")
    for sz, name in [(1, "Seizure-FREE"), (0, "NOT seizure-free")]:
        sub = df[df["seizure_free"] == sz]
        r = mcnemar_paired(sub, "preop_any_psych_dx", "postop_any_psych_dx", name + " (cum)")
        rows_sz.append(r)
        print("  " + fmt_traj(r))

    # -------- (4) Depression & anxiety subscales --------------------------------
    print("\n" + "-" * 100)
    print("(4) DEPRESSION & ANXIETY SUBSCALES: all vs excl-multi-proc")
    print("-" * 100)
    rows_sub = []
    for pre, post, nm in [("preop_depression", "postop_depression", "Depression"),
                          ("preop_anxiety", "postop_anxiety", "Anxiety")]:
        all_r = mcnemar_paired(df, pre, post, f"{nm} ALL")
        sng_r = mcnemar_paired(df_single, pre, post, f"{nm} EXCL multi-proc")
        rows_sub += [all_r, sng_r]
        print("\n  " + fmt_traj(all_r))
        print("  " + fmt_traj(sng_r))
        shift = sng_r["delta_pp"] - all_r["delta_pp"]
        print(f"    --> exclusion shifts {nm} delta by {shift:+.1f}pp.")

    # -------- (5) Multi-proc vs single-proc characteristics ---------------------
    print("\n" + "-" * 100)
    print("(5) WHY EXCLUSION IS NOT NEUTRAL: multiple_procedure==1 vs ==0")
    print("-" * 100)
    char_rows = []
    for oc, nm in [("seizure_free", "Seizure-free rate"),
                   ("preop_any_psych_dx", "Preop ANY psych"),
                   ("postop_psych_pointprev", "Postop ANY psych (point-prev)"),
                   ("postop_any_psych_dx", "Postop ANY psych (cumulative)"),
                   ("new_onset_postop_psych", "New-onset postop psych"),
                   ("preop_depression", "Preop depression"),
                   ("preop_anxiety", "Preop anxiety"),
                   ("female_n", "Female")]:
        c = chisq_2x2(df, "multiple_procedure", oc)
        char_rows.append((nm, oc, c))
        ptxt = (f"chi2 p={c['p_chi2']:.4f}" +
                (f"; Fisher p={c['p_fisher']:.4f}" if c["p_fisher"] is not None else ""))
        print(f"  {nm:32s}: multi-proc={c['rate_group1']*100:5.1f}% "
              f"(n={c['n_group1']}) vs single={c['rate_group0']*100:5.1f}% "
              f"(n={c['n_group0']}) | {ptxt}")
    # continuous: age, followup, svi by t-test-free summary
    print("\n  Continuous (mean):")
    cont_rows = []
    for col, nm in [("age", "Age (yr)"), ("followup_years", "Follow-up (yr)"),
                    ("svi", "SVI")]:
        g1 = df.loc[df["multiple_procedure"] == 1, col].dropna()
        g0 = df.loc[df["multiple_procedure"] == 0, col].dropna()
        cont_rows.append((nm, g1.mean(), g0.mean()))
        print(f"    {nm:18s}: multi-proc={g1.mean():.2f} vs single={g0.mean():.2f}")

    # seizure_free by multiple_procedure cross-tab for narrative
    sf_by_mp = pd.crosstab(df["multiple_procedure"], df["seizure_free"])
    print(f"\n  Seizure-free x multi-proc crosstab:\n{sf_by_mp}")

    print("\n" + "=" * 100)
    print("BOTTOM LINE: postop prevalence in THIS extract does NOT reproduce the")
    print("manuscript's reported decrease. Excluding multiple_procedure patients")
    print("removes a group with a different seizure-free rate and psych burden, so")
    print("the exclusion is NOT outcome-neutral (the reviewer's point).")
    print(CAVEAT)
    print("=" * 100)

    return rows_traj, rows_sz, rows_sub, char_rows, cont_rows


if __name__ == "__main__":
    main()
