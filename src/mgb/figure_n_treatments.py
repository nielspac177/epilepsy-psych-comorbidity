#!/usr/bin/env python3
"""Figure: psychiatric improvement and seizure freedom by NUMBER of treatments.
Every patient received at least one therapeutic procedure, so the count starts at 1.
Reads work/mgb_clean_review.csv; writes deliverables/figures/n_treatments.png/.pdf.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from statsmodels.stats.proportion import proportion_confint

REPO = Path(__file__).resolve().parents[2]
df = pd.read_csv(REPO / "work" / "mgb_clean_review.csv")
OUT = REPO / "deliverables" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

levels = [1, 2, 3]
labels = ["1\n(n=209)", "2\n(n=49)", "3\n(n=15)"]
color = "#3182bd"


def rates(col):
    out = []
    for k in levels:
        s = df.loc[df.n_treatments == k, col].dropna()
        n, e = len(s), int(s.sum())
        lo, hi = proportion_confint(e, n, method="wilson")
        out.append((100 * e / n, 100 * lo, 100 * hi, e, n))
    return out


def trend_p(col):
    t = pd.crosstab(df["n_treatments"], df[col])
    return sm.stats.Table(t).test_ordinal_association().pvalue


fig, axes = plt.subplots(1, 2, figsize=(9, 4.2))
for ax, col, title in [(axes[0], "improved", "A  Psychiatric improvement"),
                       (axes[1], "seizure_free", "B  Seizure freedom")]:
    r = rates(col)
    x = np.arange(len(levels))
    vals = [a[0] for a in r]
    err = [[a[0] - a[1] for a in r], [a[2] - a[0] for a in r]]
    ax.bar(x, vals, color=color, width=0.6, edgecolor="black", linewidth=0.6)
    ax.errorbar(x, vals, yerr=err, fmt="none", ecolor="black", capsize=4, linewidth=1)
    for xi, a in zip(x, r):
        ax.text(xi, a[2] + 2, f"{a[3]}/{a[4]}", ha="center", va="bottom", fontsize=8.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_xlabel("Number of treatments")
    ax.set_ylim(0, 70)
    ax.set_ylabel("Percent of patients")
    ax.set_title(title, loc="left", fontsize=11, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    ax.annotate(f"trend p={trend_p(col):.3g}", (0.5, 0.93), xycoords="axes fraction",
                ha="center", fontsize=8, style="italic")

fig.suptitle("Psychiatric improvement and seizure freedom by number of treatments (MGB)",
             fontsize=10.5, y=1.02)
fig.tight_layout()
for ext in ("png", "pdf"):
    fig.savefig(OUT / f"n_treatments.{ext}", dpi=300, bbox_inches="tight")
print("wrote", OUT / "n_treatments.png")
