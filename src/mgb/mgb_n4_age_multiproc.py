#!/usr/bin/env python3
"""
MGB analyses N4: (1) age summary, (2) multiple-procedure re-analysis of
pre->post change in "any psychiatric disorder" prevalence (Glaser comment 13).

Data: results/merged_deprivation_psych_data.csv (284 rows).

KNOWN DATA GAP: PHQ-9/GAD-7 are too sparse in this file to reproduce the
manuscript's paired n=116 (PHQ-9)/n=112 (GAD-7); not analyzed here.
"""
import pandas as pd
import numpy as np
from statsmodels.stats.contingency_tables import mcnemar

CSV = ("/Users/nielspacheco/Desktop/Research/Rolston lab/Psych_epilepsy_surgery/"
       "results/merged_deprivation_psych_data.csv")

df = pd.read_csv(CSV)
print(f"Loaded {df.shape[0]} rows x {df.shape[1]} cols\n")


def num(s):
    return pd.to_numeric(s, errors="coerce")


# ---------------------------------------------------------------------------
# (1) AGE
# ---------------------------------------------------------------------------
age = num(df["age_at_surgery"])
print("=" * 60)
print("(1) AGE AT SURGERY")
print("=" * 60)
print(f"  n non-null       : {age.notna().sum()}")
print(f"  mean +/- SD      : {age.mean():.2f} +/- {age.std(ddof=1):.2f}")
print(f"  median [min,max] : {age.median():.1f} [{age.min():.0f}, {age.max():.0f}]")
print("  Manuscript: 33.5 (abstract) / 33.3 (Table 1); n=273 there vs 284 here.\n")


# ---------------------------------------------------------------------------
# (2) MULTIPLE-PROCEDURE RE-ANALYSIS: any psych dx pre -> post
# ---------------------------------------------------------------------------
def analyze(sub, label):
    pre = num(sub["preop_any_psych_dx"])
    post = num(sub["postop_any_psych_dx"])
    ok = pre.notna() & post.notna()
    pre, post = pre[ok].astype(int), post[ok].astype(int)
    n = len(pre)
    p_pre, p_post = pre.mean(), post.mean()
    # 2x2 paired table
    b = int(((pre == 0) & (post == 1)).sum())  # gained dx
    c = int(((pre == 1) & (post == 0)).sum())  # lost dx
    a = int(((pre == 1) & (post == 1)).sum())
    d = int(((pre == 0) & (post == 0)).sum())
    tab = [[a, c], [b, d]]  # for reference
    res = mcnemar([[d, b], [c, a]], exact=(b + c) < 25)
    print(f"--- {label} (paired n={n}) ---")
    print(f"  preop  any psych dx prevalence : {p_pre*100:5.1f}%  ({pre.sum()}/{n})")
    print(f"  postop any psych dx prevalence : {p_post*100:5.1f}%  ({post.sum()}/{n})")
    print(f"  delta (post - pre)             : {(p_post-p_pre)*100:+5.1f} pp")
    print(f"  discordant: gained dx (0->1)={b}, lost dx (1->0)={c}")
    print(f"  McNemar stat={res.statistic:.3f}, p={res.pvalue:.4g}")
    return dict(n=n, pre=p_pre, post=p_post, delta=p_post - p_pre,
                gained=b, lost=c, p=res.pvalue)

print("=" * 60)
print("(2) ANY PSYCHIATRIC DISORDER: pre -> post (Glaser comment 13)")
print("=" * 60)

# (a) ALL patients (includes multiple-procedure patients)
all_res = analyze(df, "(a) ALL patients (incl. multi-procedure)")
print()

# (b) EXCLUDING patients with a subsequent/second procedure
sub_col = df["Subsequent treatment? (y/n)"].astype(str).str.strip().str.lower()
print("  'Subsequent treatment? (y/n)' values:",
      dict(sub_col.value_counts()))
excl = df[sub_col == "n"].copy()   # keep only those WITHOUT subsequent treatment
print(f"  -> excluding subsequent-treatment ('y') patients leaves {len(excl)} rows\n")
excl_res = analyze(excl, "(b) EXCLUDING subsequent-procedure patients")
print()

print("=" * 60)
print("SENSITIVITY: how much does including multi-procedure change it?")
print("=" * 60)
print(f"  delta ALL            : {all_res['delta']*100:+.1f} pp (n={all_res['n']})")
print(f"  delta EXCLUDING multi: {excl_res['delta']*100:+.1f} pp (n={excl_res['n']})")
print(f"  difference in deltas : {(all_res['delta']-excl_res['delta'])*100:+.1f} pp")

print("""
CAVEATS:
 - 'Subsequent treatment? (y/n)' = 'y' for 250/284 and 'n' for 34/284. If this
   flag truly marks a second/subsequent PROCEDURE, excluding 'y' would drop 88%
   of the cohort (implausible for "multi-procedure"). The label may instead mean
   "any subsequent treatment/follow-up," so interpretation of the exclusion is
   UNCERTAIN. The exclusion analysis is reported as instructed but should be
   verified against the data dictionary before use.
 - File has 284 rows vs manuscript n=273; numbers may not match exactly.
 - PHQ-9/GAD-7 too sparse here to reproduce paired n=116/112 (not analyzed).
""")
