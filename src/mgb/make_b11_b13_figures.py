#!/usr/bin/env python3
"""
Generate the figures for reviewer comments B11, B12, and B13 from the clean MGB
analysis dataset. Saves PNGs to an output directory (default: ./figures).

Figures:
  fig_b11_slopes.png  Paired PHQ-9 and GAD-7 trajectories (baseline -> follow-up),
                      improvers (ED50 MCID) highlighted.
  fig_b12_followup.png Follow-up length by paired vs unpaired status.
  fig_b13_trajectory.png Pre/post psychiatric prevalence: full cohort vs
                      multiple-procedure-excluded, and by seizure freedom.

Usage:
    python make_b11_b13_figures.py work/mgb_analysis_clean.csv figures/
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BLUE, ORANGE, GREY = "#1F4E79", "#E1812C", "#9AA0A6"
ED50 = {"phq9": 3.7, "gad7": 3.3}


def load(csv):
    d = pd.read_csv(csv)
    for c in ["phq9_pre", "phq9_post", "gad7_pre", "gad7_post",
              "followup_years", "preop_any_psych_dx", "postop_psych_pointprev",
              "multiple_procedure", "seizure_free"]:
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    return d


def fig_b11(d, out):
    fig, axes = plt.subplots(1, 2, figsize=(8, 4.2))
    for ax, (pre_c, post_c, name, thr) in zip(
        axes, [("phq9_pre", "phq9_post", "PHQ-9", ED50["phq9"]),
               ("gad7_pre", "gad7_post", "GAD-7", ED50["gad7"])]):
        sub = d[d[pre_c].notna() & d[post_c].notna()]
        n_imp = 0
        for _, r in sub.iterrows():
            improved = (r[pre_c] - r[post_c]) >= thr
            n_imp += int(improved)
            ax.plot([0, 1], [r[pre_c], r[post_c]],
                    color=(BLUE if improved else GREY),
                    lw=(2.0 if improved else 1.0), alpha=(0.9 if improved else 0.5),
                    marker="o", markersize=4, zorder=(3 if improved else 1))
        ax.set_xlim(-0.25, 1.25)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Baseline", "Follow-up"])
        ax.set_ylabel(f"{name} score")
        pct = 100 * n_imp / len(sub) if len(sub) else 0
        ax.set_title(f"{name}  (n={len(sub)})\n{n_imp}/{len(sub)} improved ≥ MCID ({pct:.0f}%)", fontsize=10)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Paired symptom trajectories after epilepsy surgery (improvers in blue)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out / "fig_b11_slopes.png", dpi=160)
    plt.close(fig)


def fig_b12(d, out):
    fig, axes = plt.subplots(1, 2, figsize=(8, 4.2))
    for ax, (pre_c, post_c, name) in zip(
        axes, [("phq9_pre", "phq9_post", "PHQ-9"),
               ("gad7_pre", "gad7_post", "GAD-7")]):
        paired = d[pre_c].notna() & d[post_c].notna()
        groups = [d.loc[paired, "followup_years"].dropna(), d.loc[~paired, "followup_years"].dropna()]
        parts = ax.boxplot(groups, labels=[f"Paired\n(n={groups[0].shape[0]})", f"Unpaired\n(n={groups[1].shape[0]})"],
                           patch_artist=True, widths=0.5, showfliers=False)
        for patch, col in zip(parts["boxes"], [BLUE, GREY]):
            patch.set_facecolor(col)
            patch.set_alpha(0.6)
        for i, g in enumerate(groups, start=1):
            ax.scatter(np.random.default_rng(i).normal(i, 0.05, len(g)), g, s=8, color="black", alpha=0.3, zorder=3)
        ax.set_ylabel("Follow-up length (years)")
        ax.set_title(f"{name}: follow-up by data availability", fontsize=10)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Follow-up length is similar for patients with vs without paired scores (no significant difference)", fontsize=9.5)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out / "fig_b12_followup.png", dpi=160)
    plt.close(fig)


def _prev(sub, col):
    s = sub[col].dropna()
    return 100 * s.mean(), len(s)


def fig_b13(d, out):
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 4.3))

    # Panel 1: full cohort vs multiple-procedure-excluded
    ax = axes[0]
    full_pre, _ = _prev(d, "preop_any_psych_dx")
    full_post, _ = _prev(d, "postop_psych_pointprev")
    excl = d[d["multiple_procedure"] == 0]
    ex_pre, _ = _prev(excl, "preop_any_psych_dx")
    ex_post, _ = _prev(excl, "postop_psych_pointprev")
    ax.plot([0, 1], [full_pre, full_post], "-o", color=BLUE, lw=2, label=f"Full cohort (n={len(d)})")
    ax.plot([0, 1], [ex_pre, ex_post], "-o", color=ORANGE, lw=2, label=f"Excl. multiple procedure (n={len(excl)})")
    ax.set_title("Any psychiatric disorder: pre vs post", fontsize=10)
    ax.legend(fontsize=8, frameon=False)

    # Panel 2: stratified by seizure freedom
    ax2 = axes[1]
    sf = d[d["seizure_free"] == 1]
    nsf = d[d["seizure_free"] == 0]
    ax2.plot([0, 1], [_prev(sf, "preop_any_psych_dx")[0], _prev(sf, "postop_psych_pointprev")[0]],
             "-o", color=BLUE, lw=2, label=f"Seizure-free (n={len(sf)})")
    ax2.plot([0, 1], [_prev(nsf, "preop_any_psych_dx")[0], _prev(nsf, "postop_psych_pointprev")[0]],
             "-o", color=ORANGE, lw=2, label=f"Not seizure-free (n={len(nsf)})")
    ax2.set_title("Stratified by seizure freedom", fontsize=10)
    ax2.legend(fontsize=8, frameon=False)

    for ax in axes:
        ax.set_xlim(-0.25, 1.25)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Preop", "Postop"])
        ax.set_ylabel("Psychiatric prevalence (%)")
        ax.set_ylim(0, 80)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Postoperative psychiatric trajectory (PROVISIONAL data; postop does not yet match Table 3)", fontsize=9.5)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out / "fig_b13_trajectory.png", dpi=160)
    plt.close(fig)


def main() -> int:
    csv = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("work/mgb_analysis_clean.csv")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("figures")
    out.mkdir(parents=True, exist_ok=True)
    d = load(csv)
    fig_b11(d, out)
    fig_b12(d, out)
    fig_b13(d, out)
    print("wrote figures to", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
