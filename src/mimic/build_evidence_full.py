"""Re-derive psych ICD evidence for the FULL epilepsy cohort (n=8,968)."""
import hashlib, sys, gzip
from collections import defaultdict
from pathlib import Path
import pandas as pd

MIMIC_ROOT = Path("/Volumes/Niels 2/MIMIC/physionet.org/files/mimiciv/3.1")
ANALYSIS = MIMIC_ROOT / "analysis/epilepsy_psych"
DX_FILE = MIMIC_ROOT / "hosp/diagnoses_icd.csv.gz"
COHORT_FILE = ANALYSIS / "epilepsy_patient_cohort_psm.csv"
OUT = Path("/tmp/pi_pkg")

PSY = {
    "depression":    {"icd10": ["F32", "F33", "F341"],
                      "icd9":  ["2962", "2963", "3004", "311"]},
    "anxiety":       {"icd10": ["F40", "F41"],
                      "icd9":  ["30000", "30001", "30002", "30021", "30022", "30023", "30029"]},
    "substance_use": {"icd10": ["F10","F11","F12","F13","F14","F15","F16","F17","F18","F19"],
                      "icd9":  ["303", "304", "305"]},
}

def matches(code: str, version: int, dx: str) -> bool:
    code = str(code).strip()
    pats = PSY[dx]["icd10"] if version == 10 else PSY[dx]["icd9"]
    return any(code.startswith(p) for p in pats)

cohort = pd.read_csv(COHORT_FILE)
ids = set(cohort.subject_id.astype(int).tolist())
print(f"Cohort: {len(ids):,} patients", file=sys.stderr)

evidence = defaultdict(lambda: {"depression": set(), "anxiety": set(), "substance_use": set()})
rows_seen = 0
for chunk in pd.read_csv(DX_FILE, dtype={"icd_code": str}, chunksize=500_000):
    chunk = chunk[chunk.subject_id.isin(ids)]
    rows_seen += len(chunk)
    for _, r in chunk.iterrows():
        sid = int(r.subject_id); ver = int(r.icd_version); code = r.icd_code
        for dx in PSY:
            if matches(code, ver, dx):
                evidence[sid][dx].add(f"ICD-{ver}:{code}")

print(f"Scanned {rows_seen:,} cohort-patient diagnosis rows", file=sys.stderr)

rows = []
for sid in sorted(ids):
    ev = evidence.get(sid, {})
    rows.append({
        "subject_id": sid,
        "depression_codes":    ";".join(sorted(ev.get("depression", []))),
        "anxiety_codes":       ";".join(sorted(ev.get("anxiety", []))),
        "substance_use_codes": ";".join(sorted(ev.get("substance_use", []))),
    })
df = pd.DataFrame(rows)
df.to_csv(OUT / "all_epilepsy_psych_evidence.csv", index=False)

# Consistency check vs cohort flags
ck = cohort.merge(df, on="subject_id")
miss = 0
for _, r in ck.iterrows():
    for dx, col in [("depression","has_depression"),("anxiety","has_anxiety"),("substance_use","has_substance_use")]:
        derived = bool(r[f"{dx}_codes"])
        flagged = bool(r[col])
        if derived != flagged: miss += 1
print(f"Disagreements: {miss} / {len(ck)*3}", file=sys.stderr)
print("DONE.", file=sys.stderr)
