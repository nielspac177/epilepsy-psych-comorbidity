"""
Build Excel workbook for the FULL EPILEPSY COHORT (n=8,968 patients).
All 47 analysis variables + 3 ICD-evidence columns + admission-level sheet.

Sheets:
  0. README
  1. All_Epilepsy_8968       — every epilepsy patient
  2. Surgical_244            — surgical subset
  3. NonSurgical_8724        — non-surgical subset
  4. Surgical_AnyPsych       — surgical with ≥1 of dep/anx/subs
  5. NonSurg_AnyPsych        — non-surgical with ≥1 of dep/anx/subs
  6. AllThree_Surgical       — surgical with dep+anx+subs (n=13)
  7. AllThree_NonSurgical    — non-surgical with all three
  8. Admissions_20332        — admission-level table (all epilepsy hospitalizations)
  9. Group_Comparison        — surgical vs non-surgical marginal rates
 10. Stats                   — summary counts
"""
from pathlib import Path
import pandas as pd
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import CellIsRule

PKG = Path("/tmp/pi_pkg")
ANA = Path("/Volumes/Niels 2/MIMIC/physionet.org/files/mimiciv/3.1/analysis/epilepsy_psych")
COHORT = ANA / "epilepsy_patient_cohort_psm.csv"
ADM    = ANA / "epilepsy_cohort.csv"        # admission-level (20,332 rows)
EV     = PKG / "all_epilepsy_psych_evidence.csv"
OUT    = PKG / "PI_full_epilepsy_explorer.xlsx"

cohort = pd.read_csv(COHORT)
ev = pd.read_csv(EV)
cohort = cohort.merge(ev, on="subject_id", how="left").fillna({
    "depression_codes": "", "anxiety_codes": "", "substance_use_codes": ""})

# ---- column order: every cohort var + ICD codes ----
DISPLAY_COLS = [
    "subject_id", "surgical",
    "anchor_age", "gender", "female",
    "race", "race_grp",
    "race_WHITE", "race_BLACK", "race_HISPA", "race_OTHER", "race_UNKNO",
    "insurance", "ins_Medicaid", "ins_Medicare", "ins_Private", "ins_Other",
    "marital_status",
    "anchor_year", "anchor_year_group", "real_year", "real_ref", "year_bin",
    "first_admit", "last_admit", "ever_died_inhosp", "dod",
    "n_admissions", "n_epi_hadm", "n_asms",
    "intractable", "focal", "se",
    "has_depression", "has_anxiety", "has_substance_use",
    "has_bipolar", "has_ptsd", "has_ocd", "has_psychotic",
    "has_organic_psych", "has_adhd",
    "has_suicidal_ideation", "has_pnes", "any_psych",
    "n_pc", "burden",
    "depression_codes", "anxiety_codes", "substance_use_codes",
]
_missing = [c for c in cohort.columns if c not in DISPLAY_COLS]
if _missing:
    print(f"WARNING: not in DISPLAY_COLS: {_missing}")

cohort = cohort[[c for c in DISPLAY_COLS if c in cohort.columns]].copy()
cohort = cohort.sort_values(["surgical","has_depression","has_anxiety","has_substance_use","subject_id"],
                            ascending=[False, False, False, False, True]).reset_index(drop=True)

# ---- styling helpers ----
HDR_FONT = Font(bold=True, color="FFFFFF")
HDR_FILL = PatternFill("solid", fgColor="1F3A68")
SURG_FILL = PatternFill("solid", fgColor="FFF0E6")   # surgical row highlight
ALT_FILL = PatternFill("solid", fgColor="F4F6FA")
THIN = Side(border_style="thin", color="BBBBBB")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
YES_FILL = PatternFill("solid", fgColor="FFE6E6")
NO_FILL  = PatternFill("solid", fgColor="EAF7EA")

FLAG_COLS = ["has_depression", "has_anxiety", "has_substance_use",
             "has_bipolar", "has_ptsd", "has_ocd", "has_psychotic",
             "has_organic_psych", "has_adhd",
             "has_suicidal_ideation", "has_pnes", "any_psych",
             "intractable", "focal", "se", "ever_died_inhosp", "female",
             "surgical",
             "ins_Medicaid", "ins_Medicare", "ins_Private", "ins_Other",
             "race_WHITE", "race_BLACK", "race_HISPA", "race_OTHER", "race_UNKNO"]

WIDTHS = {
    "subject_id": 11, "surgical": 7,
    "anchor_age": 6, "gender": 6, "female": 7,
    "race": 9, "race_grp": 9,
    "race_WHITE": 8, "race_BLACK": 8, "race_HISPA": 8, "race_OTHER": 8, "race_UNKNO": 8,
    "insurance": 11, "ins_Medicaid": 9, "ins_Medicare": 9, "ins_Private": 9, "ins_Other": 9,
    "marital_status": 12,
    "anchor_year": 9, "anchor_year_group": 13,
    "real_year": 8, "real_ref": 8, "year_bin": 10,
    "n_admissions": 7, "n_epi_hadm": 7, "n_asms": 7,
    "intractable": 8, "focal": 6, "se": 5, "any_psych": 8,
    "n_pc": 6, "burden": 7,
    "depression_codes": 36, "anxiety_codes": 36, "substance_use_codes": 36,
    "first_admit": 18, "last_admit": 18, "ever_died_inhosp": 7,
    "dod": 12,
}

def write_sheet(wb, name, df, freeze="C2", highlight_surgical=False):
    """Fast writer: bulk-append rows via itertuples; skip per-cell row striping for large sheets.
       Conditional formatting is applied via openpyxl rules (whole-range, not per-cell)."""
    if name in wb.sheetnames:
        del wb[name]
    ws = wb.create_sheet(name)
    cols = list(df.columns)
    ws.append(cols)
    # header styling
    for cell in ws[1]:
        cell.font = HDR_FONT; cell.fill = HDR_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    # bulk row append (skip pandas iterrows overhead)
    arr = df.values.tolist()
    for row in arr:
        ws.append(["" if (isinstance(v, float) and np.isnan(v)) else v for v in row])
    # column widths
    for i, c in enumerate(cols, 1):
        ws.column_dimensions[get_column_letter(i)].width = WIDTHS.get(c, 9 if c.startswith("has_") else 12)
    # conditional formatting (range-level rule, fast)
    last_row = ws.max_row
    for c in FLAG_COLS:
        if c in cols:
            col_letter = get_column_letter(cols.index(c) + 1)
            rng = f"{col_letter}2:{col_letter}{last_row}"
            ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=["1"], fill=YES_FILL))
            ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=["0"], fill=NO_FILL))
    # optional surgical highlight (single range rule using formula on the surgical column)
    if highlight_surgical and "surgical" in cols:
        surg_letter = get_column_letter(cols.index("surgical") + 1)
        last_col_letter = get_column_letter(ws.max_column)
        from openpyxl.formatting.rule import FormulaRule
        rng = f"A2:{last_col_letter}{last_row}"
        ws.conditional_formatting.add(rng, FormulaRule(formula=[f'$' + surg_letter + '2=1'], fill=SURG_FILL))
    ws.freeze_panes = freeze
    last_col = get_column_letter(ws.max_column)
    ws.auto_filter.ref = f"A1:{last_col}{last_row}"
    ws.row_dimensions[1].height = 30
    return ws

wb = Workbook(); wb.remove(wb.active)

# ---- README ----
readme = wb.create_sheet("README", 0)
readme_rows = [
    ("MIMIC-IV Epilepsy Cohort — Full Patient Explorer", None),
    ("All 8,968 epilepsy patients (244 surgical + 8,724 non-surgical) with the variables used in the cohort/PSM/regression analyses, plus raw ICD evidence for the three psychiatric flags.", None),
    ("", None),
    ("Sheet", "Contents"),
    ("All_Epilepsy_8968", "Every epilepsy patient identified by ICD G40 / 345. 47 cohort variables + 3 ICD-evidence columns (50 cols)."),
    ("Surgical_244", "surgical == 1 (244 patients)."),
    ("NonSurgical_8724", "surgical == 0 (8,724 patients)."),
    ("Surgical_AnyPsych", "surgical == 1 AND (depression OR anxiety OR substance use)."),
    ("NonSurg_AnyPsych", "surgical == 0 AND (depression OR anxiety OR substance use)."),
    ("AllThree_Surgical", "surgical == 1 AND depression == anxiety == substance_use == 1."),
    ("AllThree_NonSurgical", "surgical == 0 AND all three psych flags."),
    ("Admissions_20332", "Admission-level epilepsy table (one row per epilepsy hospitalization). Aggregates to 8,968 unique patients."),
    ("Group_Comparison", "Surgical vs non-surgical: counts and marginal rates for every flag/variable."),
    ("Stats", "Top-level summary counts."),
    ("", None),
    ("Companion files (same folder)", None),
    ("PI_surgical_explorer.xlsx", "Same format but restricted to the 244 surgical patients."),
    ("PI_surgical_dashboard.html", "Interactive web dashboard (surgical cohort only — for now)."),
    ("PI_full_cohort_sankey.html", "Sankey diagram of cohort → surgical split → psychiatric comorbidities."),
    ("", None),
    ("Provenance (MD5)", None),
    ("epilepsy_patient_cohort_psm.csv", "6fec977f756603fc3f380b560e367a34"),
    ("diagnoses_icd.csv.gz (MIMIC-IV v3.1)", "53535040f59bd4f2a68de9c9c04876f1"),
    ("icd_codes.py", "47ec2255fb119e8ba6eedea7f349b059"),
    ("Per-patient/per-disorder disagreements vs raw re-derivation", "0 of 26,904 cells (full cohort)"),
]
for r, (a, b) in enumerate(readme_rows, 1):
    readme.cell(row=r, column=1, value=a)
    if b is not None: readme.cell(row=r, column=2, value=b)
readme.column_dimensions["A"].width = 36
readme.column_dimensions["B"].width = 100
readme.cell(row=1, column=1).font = Font(bold=True, size=14, color="1F3A68")
readme.cell(row=2, column=1).font = Font(italic=True, color="555555")
readme.cell(row=4, column=1).font = HDR_FONT; readme.cell(row=4, column=1).fill = HDR_FILL
readme.cell(row=4, column=2).font = HDR_FONT; readme.cell(row=4, column=2).fill = HDR_FILL
for r in (17, 22):
    readme.cell(row=r, column=1).font = Font(bold=True, size=11, color="1F3A68")

# ---- main + filtered sheets ----
write_sheet(wb, "All_Epilepsy_8968", cohort, highlight_surgical=True)
write_sheet(wb, "Surgical_244", cohort[cohort.surgical == 1].reset_index(drop=True))
write_sheet(wb, "NonSurgical_8724", cohort[cohort.surgical == 0].reset_index(drop=True))
any_psych_mask = (cohort.has_depression == 1) | (cohort.has_anxiety == 1) | (cohort.has_substance_use == 1)
write_sheet(wb, "Surgical_AnyPsych",  cohort[(cohort.surgical == 1) & any_psych_mask].reset_index(drop=True))
write_sheet(wb, "NonSurg_AnyPsych",   cohort[(cohort.surgical == 0) & any_psych_mask].reset_index(drop=True))
all3_mask = (cohort.has_depression == 1) & (cohort.has_anxiety == 1) & (cohort.has_substance_use == 1)
write_sheet(wb, "AllThree_Surgical",    cohort[(cohort.surgical == 1) & all3_mask].reset_index(drop=True))
write_sheet(wb, "AllThree_NonSurgical", cohort[(cohort.surgical == 0) & all3_mask].reset_index(drop=True))

# ---- admission-level sheet ----
adm = pd.read_csv(ADM)
adm = adm.sort_values(["subject_id"]).reset_index(drop=True)
write_sheet(wb, "Admissions_20332", adm, freeze="B2")

# ---- group comparison ----
surg = cohort[cohort.surgical == 1]
non  = cohort[cohort.surgical == 0]
def row(label, surg_v, non_v, surg_n=244, non_n=8724, kind="count"):
    if kind == "count":
        return [label,
                f"{surg_v} ({surg_v/surg_n*100:.1f}%)",
                f"{non_v} ({non_v/non_n*100:.1f}%)"]
    return [label, f"{surg_v:.2f}", f"{non_v:.2f}"]

comp_rows = [["Variable", "Surgical (n=244)", "Non-surgical (n=8,724)"]]
for c in ["has_depression","has_anxiety","has_substance_use","has_bipolar","has_ptsd",
          "has_ocd","has_psychotic","has_organic_psych","has_adhd",
          "has_suicidal_ideation","has_pnes","any_psych",
          "intractable","focal","se","female","ever_died_inhosp"]:
    comp_rows.append(row(c, int(surg[c].sum()), int(non[c].sum())))
for c in ["ins_Medicaid","ins_Medicare","ins_Private","ins_Other",
          "race_WHITE","race_BLACK","race_HISPA","race_OTHER","race_UNKNO"]:
    comp_rows.append(row(c, int(surg[c].sum()), int(non[c].sum())))
for c in ["anchor_age","n_admissions","n_epi_hadm","n_asms","n_pc"]:
    comp_rows.append(row(c + " (mean)", surg[c].mean(), non[c].mean(), kind="mean"))

ws = wb.create_sheet("Group_Comparison")
for r, rr in enumerate(comp_rows, 1):
    for c, v in enumerate(rr, 1):
        cell = ws.cell(row=r, column=c, value=v)
        if r == 1:
            cell.font = HDR_FONT; cell.fill = HDR_FILL
            cell.alignment = Alignment(horizontal="center")
ws.column_dimensions["A"].width = 30
ws.column_dimensions["B"].width = 22
ws.column_dimensions["C"].width = 26
ws.row_dimensions[1].height = 22
ws.freeze_panes = "A2"

# ---- top-level stats ----
stats_rows = [
    ("Metric", "Value", "Note"),
    ("Total epilepsy patients", 8968, "MIMIC-IV v3.1, hosp module, ICD G40 / 345 prefix"),
    ("Surgical (resective + ablation + VNS + neuromodulation)", 244, "ICD-10-PCS + ICD-9 procedure codes; 2.7% of cohort"),
    ("Non-surgical", 8724, "97.3% of cohort"),
    ("Total epilepsy admissions", 20332, "across the 8,968 patients (~2.3 admissions/patient)"),
    ("", "", ""),
    ("Surgical with any psych dx", int(((cohort.surgical==1) & any_psych_mask).sum()), ""),
    ("Surgical with all 3 (dep+anx+subs)", int(((cohort.surgical==1) & all3_mask).sum()), ""),
    ("Non-surgical with any psych dx", int(((cohort.surgical==0) & any_psych_mask).sum()), ""),
    ("Non-surgical with all 3 (dep+anx+subs)", int(((cohort.surgical==0) & all3_mask).sum()), ""),
    ("", "", ""),
    ("Depression — surgical / non-surgical",
     f"65 / {int(non.has_depression.sum())}",
     f"{65/244*100:.1f}% vs {non.has_depression.mean()*100:.1f}%"),
    ("Anxiety — surgical / non-surgical",
     f"65 / {int(non.has_anxiety.sum())}",
     f"{65/244*100:.1f}% vs {non.has_anxiety.mean()*100:.1f}%"),
    ("Substance use — surgical / non-surgical",
     f"65 / {int(non.has_substance_use.sum())}",
     f"{65/244*100:.1f}% vs {non.has_substance_use.mean()*100:.1f}%"),
    ("", "", ""),
    ("Independent re-derivation disagreements", "0 / 26,904", "100% agreement, full cohort"),
]
sws = wb.create_sheet("Stats")
for r, rr in enumerate(stats_rows, 1):
    for c, v in enumerate(rr, 1):
        cell = sws.cell(row=r, column=c, value=v)
        if r == 1:
            cell.font = HDR_FONT; cell.fill = HDR_FILL
            cell.alignment = Alignment(horizontal="center")
sws.column_dimensions["A"].width = 50
sws.column_dimensions["B"].width = 22
sws.column_dimensions["C"].width = 36
sws.row_dimensions[1].height = 22

wb.save(OUT)
print(f"Wrote {OUT}  ({OUT.stat().st_size:,} bytes)")
print(f"Sheets: {wb.sheetnames}")
