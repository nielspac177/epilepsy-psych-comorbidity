"""Build Sankey diagram for the full epilepsy cohort flow.
Stage 1: All Epilepsy (8,968)
Stage 2: Surgical (244) / Non-surgical (8,724)
Stage 3: For each, 4 disjoint comorbidity buckets:
         - All three (dep+anx+subs)
         - Exactly two of three
         - Exactly one of three
         - None of the three
Static PNG via matplotlib + interactive HTML via plotly.
"""
import pandas as pd
import numpy as np
from pathlib import Path

PKG = Path("/tmp/pi_pkg")
COHORT = Path("/Volumes/Niels 2/MIMIC/physionet.org/files/mimiciv/3.1/analysis/epilepsy_psych/epilepsy_patient_cohort_psm.csv")

df = pd.read_csv(COHORT)
df["n_of_three"] = df.has_depression + df.has_anxiety + df.has_substance_use

def counts(mask):
    return {
        "All three":            int(((df[mask].n_of_three) == 3).sum()),
        "Two of three":         int(((df[mask].n_of_three) == 2).sum()),
        "One of three":         int(((df[mask].n_of_three) == 1).sum()),
        "None of three":        int(((df[mask].n_of_three) == 0).sum()),
    }

surg_c = counts(df.surgical == 1)
nons_c = counts(df.surgical == 0)
total_surg = sum(surg_c.values()); total_nons = sum(nons_c.values())
assert total_surg == 244 and total_nons == 8724, (total_surg, total_nons)

# ---- nodes ----
# 0: All Epilepsy 8,968
# 1: Surgical 244
# 2: Non-surgical 8,724
# 3-6: Surgical buckets (4)
# 7-10: Non-surgical buckets (4)
labels = [
    f"All Epilepsy  ·  8,968",
    f"Surgical  ·  244",
    f"Non-surgical  ·  8,724",
    f"Surgical · All three  ·  {surg_c['All three']}",
    f"Surgical · Two of three  ·  {surg_c['Two of three']}",
    f"Surgical · One of three  ·  {surg_c['One of three']}",
    f"Surgical · None  ·  {surg_c['None of three']}",
    f"Non-surg · All three  ·  {nons_c['All three']}",
    f"Non-surg · Two of three  ·  {nons_c['Two of three']}",
    f"Non-surg · One of three  ·  {nons_c['One of three']}",
    f"Non-surg · None  ·  {nons_c['None of three']}",
]

# Node colors: stage-based gradient
node_colors = [
    "#1F3A68",                                    # all epilepsy (dark blue)
    "#C0392B",                                    # surgical (red)
    "#2874A6",                                    # non-surgical (blue)
    # surgical category nodes — darker reds for higher burden
    "#7B241C", "#C0392B", "#E59866", "#82E0AA",
    # non-surg category nodes — same gradient in blue
    "#1B4F72", "#2874A6", "#85C1E9", "#82E0AA",
]
# Link colors: tinted versions of source node
def tint(hex_color, alpha=0.5):
    return f"rgba({int(hex_color[1:3],16)},{int(hex_color[3:5],16)},{int(hex_color[5:7],16)},{alpha})"

sources = [0,0, 1,1,1,1, 2,2,2,2]
targets = [1,2, 3,4,5,6, 7,8,9,10]
values  = [244, 8724,
           surg_c["All three"], surg_c["Two of three"], surg_c["One of three"], surg_c["None of three"],
           nons_c["All three"], nons_c["Two of three"], nons_c["One of three"], nons_c["None of three"]]
link_colors = [
    tint("#C0392B", 0.55), tint("#2874A6", 0.55),                 # stage 1→2
    tint("#7B241C", 0.6), tint("#C0392B", 0.55), tint("#E59866", 0.55), tint("#82E0AA", 0.45),  # surg → buckets
    tint("#1B4F72", 0.6), tint("#2874A6", 0.55), tint("#85C1E9", 0.55), tint("#82E0AA", 0.45),  # non-surg → buckets
]

# ---- Plotly interactive HTML ----
try:
    import plotly.graph_objects as go
    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(pad=18, thickness=22, line=dict(color="black", width=0.6),
                  label=labels, color=node_colors,
                  hovertemplate="%{label}<br>n = %{value}<extra></extra>"),
        link=dict(source=sources, target=targets, value=values, color=link_colors,
                  hovertemplate="%{source.label} → %{target.label}<br>n = %{value}<extra></extra>"),
    ))
    fig.update_layout(
        title=dict(text="MIMIC-IV Epilepsy Cohort Flow — surgical split and psychiatric comorbidity pattern",
                   font=dict(size=15, color="#1F3A68")),
        font=dict(family="-apple-system, system-ui, sans-serif", size=12, color="#1a1a1a"),
        paper_bgcolor="#f7f9fc",
        margin=dict(l=20, r=20, t=70, b=80),
        height=560,
        annotations=[
            dict(text="Source: MIMIC-IV v3.1 · cohort MD5 6fec977f… · 8,968 patients · 20,332 admissions. "
                       "Buckets are mutually exclusive (sum back to 8,968).",
                 showarrow=False, xref="paper", yref="paper", x=0.5, y=-0.12,
                 font=dict(size=10.5, color="#666")),
        ],
    )
    out_html = PKG / "PI_full_cohort_sankey.html"
    fig.write_html(str(out_html), include_plotlyjs="inline", full_html=True,
                   config={"displaylogo": False, "responsive": True})
    print(f"Wrote {out_html}  ({out_html.stat().st_size:,} bytes)")
    try:
        out_png = PKG / "PI_full_cohort_sankey.png"
        fig.write_image(str(out_png), width=1400, height=600, scale=2)
        print(f"Wrote {out_png}")
    except Exception as e:
        print(f"  (PNG export skipped: {e})")
except ImportError:
    print("plotly not installed — falling back to matplotlib")

# ---- Static matplotlib version (always produced) ----
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.path import Path as MplPath

fig, ax = plt.subplots(figsize=(14, 7))
ax.set_xlim(0, 10); ax.set_ylim(0, 10)
ax.axis("off")

def block(ax, x, y_center, height, label, color, width=0.8):
    y_bot = y_center - height/2
    rect = mpatches.Rectangle((x, y_bot), width, height, facecolor=color,
                              edgecolor="black", linewidth=0.7)
    ax.add_patch(rect)
    ax.text(x + width/2, y_center, label, ha="center", va="center",
            fontsize=10, fontweight="bold", color="white" if color != "#82E0AA" else "#1a1a1a")
    return x, y_center, height

# Layout (logarithmic-ish heights so the 8,724 fits but 244 is still visible)
import math
def h(n, total=8968, max_h=6, min_h=0.25):
    """Sqrt scaling so the small surgical group is visible but proportional-ish."""
    return max(min_h, max_h * math.sqrt(n / total))

# Stage 1
y_root = 5
H_root = 7.5
ax.add_patch(mpatches.Rectangle((0.3, y_root - H_root/2), 0.7, H_root,
                                facecolor="#1F3A68", edgecolor="black", linewidth=0.7))
ax.text(0.65, y_root, "All Epilepsy\n8,968", ha="center", va="center",
        fontsize=11, fontweight="bold", color="white")

# Stage 2
y_surg = 8.5
y_nons = 3.5
H_surg = h(244)
H_nons = h(8724)
ax.add_patch(mpatches.Rectangle((3.5, y_surg - H_surg/2), 0.7, H_surg,
                                facecolor="#C0392B", edgecolor="black", linewidth=0.7))
ax.text(3.85, y_surg, f"Surgical\n244 (2.7%)", ha="center", va="center",
        fontsize=10, fontweight="bold", color="white")
ax.add_patch(mpatches.Rectangle((3.5, y_nons - H_nons/2), 0.7, H_nons,
                                facecolor="#2874A6", edgecolor="black", linewidth=0.7))
ax.text(3.85, y_nons, f"Non-surgical\n8,724 (97.3%)", ha="center", va="center",
        fontsize=10, fontweight="bold", color="white")

# Stage 3: 4 buckets per side
buckets_surg = [("All three",   surg_c["All three"],   "#7B241C"),
                ("Two of three",surg_c["Two of three"],"#C0392B"),
                ("One of three",surg_c["One of three"],"#E59866"),
                ("None",        surg_c["None of three"],"#82E0AA")]
buckets_nons = [("All three",   nons_c["All three"],   "#1B4F72"),
                ("Two of three",nons_c["Two of three"],"#2874A6"),
                ("One of three",nons_c["One of three"],"#85C1E9"),
                ("None",        nons_c["None of three"],"#82E0AA")]

def stack_buckets(buckets, y_center, total_h, x):
    total = sum(b[1] for b in buckets)
    y = y_center + total_h/2
    coords = []
    for lbl, n, col in buckets:
        hh = max(0.15, total_h * (n / total)) if total > 0 else 0.15
        y -= hh
        ax.add_patch(mpatches.Rectangle((x, y), 0.7, hh, facecolor=col,
                                        edgecolor="black", linewidth=0.5))
        text_color = "white" if col not in ("#85C1E9", "#82E0AA", "#E59866") else "#1a1a1a"
        if hh > 0.4:
            ax.text(x + 0.35, y + hh/2, f"{lbl}: {n}", ha="center", va="center",
                    fontsize=8.5, fontweight="bold", color=text_color)
        ax.text(x + 0.85, y + hh/2, f"{lbl}: {n}", ha="left", va="center",
                fontsize=9, color="#1a1a1a")
        coords.append((x, y, hh, n))
    return coords

surg_coords = stack_buckets(buckets_surg, y_surg, H_surg + 1.2, 7.0)
nons_coords = stack_buckets(buckets_nons, y_nons, H_nons + 0.5, 7.0)

# ---- Flow ribbons ----
def ribbon(ax, x1, y1, h1, x2, y2, h2, color, alpha=0.35):
    """Bezier-like ribbon from source rect right edge to target left edge."""
    # corners: source right (x1, y1) top -> bottom; target left (x2, y2) top -> bottom
    verts = [
        (x1, y1),                            # source top
        ((x1+x2)/2, y1), ((x1+x2)/2, y2),    # control points
        (x2, y2),                            # target top
        (x2, y2 - h2),                       # target bottom
        ((x1+x2)/2, y2 - h2), ((x1+x2)/2, y1 - h1),  # control points
        (x1, y1 - h1),                       # source bottom
        (x1, y1),                            # close
    ]
    codes = [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
             MplPath.LINETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4, MplPath.CLOSEPOLY]
    path = MplPath(verts, codes)
    patch = mpatches.PathPatch(path, facecolor=color, alpha=alpha, edgecolor="none")
    ax.add_patch(patch)

# Stage 1 → 2 ribbons
ribbon(ax, 1.0, y_root + H_root/2, 244/8968*H_root, 3.5, y_surg + H_surg/2, H_surg, "#C0392B")
ribbon(ax, 1.0, y_root + H_root/2 - 244/8968*H_root, H_root - 244/8968*H_root, 3.5, y_nons + H_nons/2, H_nons, "#2874A6")

# Stage 2 → 3 ribbons (surgical)
y_cur = y_surg + H_surg/2
for (x, y, hh, n), (lbl, _, col) in zip(surg_coords, buckets_surg):
    ribbon(ax, 4.2, y_cur, hh*0.95, 7.0, y + hh, hh, col, alpha=0.4)
    y_cur -= hh*0.95

# Stage 2 → 3 ribbons (non-surgical)
y_cur = y_nons + H_nons/2
for (x, y, hh, n), (lbl, _, col) in zip(nons_coords, buckets_nons):
    ribbon(ax, 4.2, y_cur, hh*0.95, 7.0, y + hh, hh, col, alpha=0.4)
    y_cur -= hh*0.95

ax.set_title("MIMIC-IV Epilepsy Cohort Flow — surgical split and psychiatric comorbidity pattern",
             fontsize=13, fontweight="bold", color="#1F3A68", pad=12)
ax.text(5, 0.5, "8,968 epilepsy patients · 244 surgical (2.7%) · 8,724 non-surgical (97.3%) · "
                "buckets are mutually exclusive (sum back to total)",
        ha="center", va="center", fontsize=9.5, style="italic", color="#666")
plt.tight_layout()
plt.savefig(PKG / "PI_full_cohort_sankey_static.png", dpi=180, bbox_inches="tight")
print(f"Wrote {PKG/'PI_full_cohort_sankey_static.png'}")

# ---- Summary printed ----
print("\nFlow summary:")
print(f"  All Epilepsy = 8,968")
print(f"    Surgical 244:")
for k,v in surg_c.items(): print(f"      {k}: {v}")
print(f"    Non-surgical 8,724:")
for k,v in nons_c.items(): print(f"      {k}: {v}")
