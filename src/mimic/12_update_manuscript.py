"""
Update manuscript & supplement per 2026-04-18 review:
  - Drop eS2.4 (suicidality/DRE analysis section) from supplement
  - Drop eFigure S5 caption (kept only by reference in main text, not shown)
  - Add a single Discussion sentence acknowledging the conceptual
    replication of Barnard et al. was not feasible.
"""
from pathlib import Path
from docx import Document

DIR = Path("/Users/nielspacheco/Desktop/Research/Rolston lab/"
           "Psych_epilepsy_surgery/Final_version_04182026")
SUP = DIR / "Manuscript 3 Epi_psych (1).docx"
MAIN = DIR / "Manuscript 3 Epi_psych.docx"
OUT_SUP  = DIR / "Manuscript 3 Epi_psych (1)_updated.docx"
OUT_MAIN = DIR / "Manuscript 3 Epi_psych_updated.docx"

# ---------- Supplement ----------
doc = Document(SUP)
paragraphs = doc.paragraphs

def del_paragraph(p):
    p._element.getparent().remove(p._element)
    p._p = p._element = None

# eS2.4 section: paragraphs 52 through 60 inclusive (header + 8 paragraphs)
# followed by a few blank paragraphs (61-65) that we also remove
# Identify by text to be safe across docx re-saves.
to_remove = []
for p in paragraphs:
    t = p.text
    if t.startswith("eS2.4 Suicidality Analysis"):
        to_remove.append(p); in_es24 = True; continue
    if t.startswith("[AUTHORS’ NOTE: The specific DRE"): to_remove.append(p); continue
    if t.startswith("A recent study from the Human Epilepsy Project (HEP) demonstrated that suicidality"): to_remove.append(p); continue
    if t.startswith("BWH cohort: Suicidality was coded in only 3 patients"): to_remove.append(p); continue
    if t.startswith("MIMIC-IV cohort: MIMIC-IV represents the best available dataset"): to_remove.append(p); continue
    if t.startswith("Among non-surgical epilepsy patients with ICD-coded suicidality"): to_remove.append(p); continue
    if t.startswith("However, two critical barriers prevent this from constituting"): to_remove.append(p); continue
    if t.startswith("NIS cohort: Suicidality was coded in only 0.3%"): to_remove.append(p); continue
    if t.startswith("Conclusion: A direct methodological replication of Barnard"): to_remove.append(p); continue
    # eFigure S5 caption + placeholder note
    if t.startswith("eFigure S5. Suicidality Ascertainment"): to_remove.append(p); continue
    if t.startswith("(A) Suicidality prevalence varied dramatically by ascertainment method"): to_remove.append(p); continue

for p in to_remove:
    del_paragraph(p)

print(f"Supplement: removed {len(to_remove)} paragraphs from eS2.4 and eFigure S5")
doc.save(OUT_SUP)

# ---------- Main manuscript ----------
doc = Document(MAIN)

TARGET_START = "The prevalence of suicidality (coded as suicidal ideation"
ADDITION = (
    " A formal conceptual replication of this finding was not feasible in our data: "
    "administrative ICD coding captured suicidality in only 5–8% of epilepsy patients, "
    "compared with 22% detected by structured C-SSRS screening in the Human Epilepsy Project, "
    "and MIMIC-IV admissions cannot be reliably anchored to the time of epilepsy diagnosis, "
    "precluding the temporal design used by Barnard and colleagues."
)

done = False
for p in doc.paragraphs:
    if p.text.startswith(TARGET_START) and not done:
        # Append sentence in the LAST run to inherit trailing formatting / font
        if p.runs:
            p.runs[-1].text = p.runs[-1].text + ADDITION
        else:
            p.add_run(ADDITION)
        done = True
        print("Main: inserted Barnard-replication limitation sentence in Discussion paragraph")
        break

if not done:
    print("WARNING: Discussion target paragraph not found; nothing inserted in main.")
doc.save(OUT_MAIN)
print("\nWrote:\n  " + str(OUT_SUP) + "\n  " + str(OUT_MAIN))
