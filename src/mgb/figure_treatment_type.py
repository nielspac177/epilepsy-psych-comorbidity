#!/usr/bin/env python3
"""Two-panel figure for Adam's treatment-type analysis.
A: postoperative psychiatric improvement rate by treatment group (Wilson 95% CI).
B: seizure-freedom rate by treatment group (the confounder by indication).
Reads work/mgb_clean_review.csv; writes deliverables/figures/treatment_type.png/.pdf.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from statsmodels.stats.proportion import proportion_confint

REPO = Path(__file__).resolve().parents[2]
df = pd.read_csv(REPO / "work" / "mgb_clean_review.csv")
OUT = REPO / "deliverables" / "figures"
OUT.mkdir(parents=True, exist_ok=True)


def fisher_p(col):
    sub = df[df.treatment_group.isin(["RES_ABLATIVE", "NEUROMOD"])]
    tab = pd.crosstab(sub.treatment_group, sub[col])
    return stats.fisher_exact(tab.values)[1]

order = ["RES_ABLATIVE", "NEUROMOD"]
labels = ["Resective/\nablative\n(n=227)", "Neuro-\nmodulation\n(n=46)"]
colors = ["#2c7fb8", "#d95f0e"]


def rates(col):
    out = []
    for g in order:
        s = df.loc[df.treatment_group == g, col].dropna()
        k, n = int(s.sum()), len(s)
        lo, hi = proportion_confint(k, n, method="wilson")
        out.append((100 * k / n, 100 * lo, 100 * hi, k, n))
    return out


fig, axes = plt.subplots(1, 2, figsize=(9, 4.2))
for ax, col, title in [(axes[0], "improved", "A  Psychiatric improvement"),
                       (axes[1], "seizure_free", "B  Seizure freedom (confounder)")]:
    r = rates(col)
    x = np.arange(len(order))
    vals = [a[0] for a in r]
    err = [[a[0] - a[1] for a in r], [a[2] - a[0] for a in r]]
    ax.bar(x, vals, color=colors, width=0.62, edgecolor="black", linewidth=0.6)
    ax.errorbar(x, vals, yerr=err, fmt="none", ecolor="black", capsize=4, linewidth=1)
    for xi, a in zip(x, r):
        ax.text(xi, a[2] + 2, f"{a[3]}/{a[4]}", ha="center", va="bottom", fontsize=8.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylim(0, 70)
    ax.set_ylabel("Percent of patients")
    ax.set_title(title, loc="left", fontsize=11, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)

_pi = fisher_p("improved")
if _pi < 0.99:  # omit an uninformative p of 1.0
    axes[0].annotate(f"Fisher p={_pi:.3g} (res vs neuromod)", (0.5, 0.93),
                     xycoords="axes fraction", ha="center", fontsize=8, style="italic")
axes[1].annotate(f"Fisher p={fisher_p('seizure_free'):.3g} (res vs neuromod)", (0.5, 0.93),
                 xycoords="axes fraction", ha="center", fontsize=8, style="italic")
fig.suptitle("Psychiatric improvement and seizure freedom by treatment group (MGB)",
             fontsize=10.5, y=1.02)
fig.tight_layout()
for ext in ("png", "pdf"):
    fig.savefig(OUT / f"treatment_type.{ext}", dpi=300, bbox_inches="tight")
print("wrote", OUT / "treatment_type.png")
