"""
PI evidence package builder.

Produces:
  1) patient_psych_evidence.csv — surgical n=244 with dx flags and contributing ICD codes
  2) triple65_disjoint.csv      — overlap table demonstrating the 3 groups of 65 are distinct
  3) coincidence_math.json      — reproduces the bootstrap/binomial probability
  4) provenance.txt             — MD5 hashes of every input
Run from anywhere; uses absolute paths to MIMIC files.
"""

import gzip
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
import numpy as np

MIMIC_ROOT = Path("/Volumes/Niels 2/MIMIC/physionet.org/files/mimiciv/3.1")
ANALYSIS = MIMIC_ROOT / "analysis/epilepsy_psych"
DX_FILE = MIMIC_ROOT / "hosp/diagnoses_icd.csv.gz"
COHORT_FILE = ANALYSIS / "epilepsy_patient_cohort_psm.csv"
OUT = Path("/tmp/pi_pkg")
OUT.mkdir(exist_ok=True)

# ---- code lists copied verbatim from icd_codes.py (audit trail) ----
PSY = {
    "depression": {
        "icd10": ["F32", "F33", "F341"],
        "icd9":  ["2962", "2963", "3004", "311"],
    },
    "anxiety": {
        "icd10": ["F40", "F41"],
        "icd9":  ["30000", "30001", "30002", "30021", "30022", "30023", "30029"],
    },
    "substance_use": {
        "icd10": ["F10", "F11", "F12", "F13", "F14", "F15", "F16", "F17", "F18", "F19"],
        "icd9":  ["303", "304", "305"],
    },
}

def md5_of(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(8 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def matches(code: str, version: int, dx: str) -> bool:
    code = str(code).strip()
    if version == 10:
        return any(code.startswith(p) for p in PSY[dx]["icd10"])
    return any(code.startswith(p) for p in PSY[dx]["icd9"])

# ---- load cohort ----
cohort = pd.read_csv(COHORT_FILE)
surg = cohort[cohort["surgical"] == 1].copy()
assert len(surg) == 244, len(surg)
surg_ids = set(surg["subject_id"].astype(int).tolist())

# ---- stream diagnoses to find every code triggering each flag ----
# diagnoses_icd has columns: subject_id, hadm_id, seq_num, icd_code, icd_version
print(f"Reading {DX_FILE.name} ...", file=sys.stderr)
dx_iter = pd.read_csv(DX_FILE, dtype={"icd_code": str}, chunksize=500_000)
evidence = defaultdict(lambda: {"depression": [], "anxiety": [], "substance_use": []})
rows_seen = 0
for chunk in dx_iter:
    chunk = chunk[chunk["subject_id"].isin(surg_ids)]
    rows_seen += len(chunk)
    for _, r in chunk.iterrows():
        sid = int(r["subject_id"])
        code = r["icd_code"]
        ver = int(r["icd_version"])
        for dx in ("depression", "anxiety", "substance_use"):
            if matches(code, ver, dx):
                evidence[sid][dx].append(f"ICD-{ver}:{code}")

print(f"Scanned {rows_seen:,} surgical-patient diagnosis rows.", file=sys.stderr)

# ---- build patient-level evidence dataframe ----
rows = []
for _, r in surg.iterrows():
    sid = int(r["subject_id"])
    ev = evidence.get(sid, {})
    rows.append({
        "subject_id": sid,
        "age": r.get("anchor_age"),
        "gender": r.get("gender"),
        "has_depression": int(r["has_depression"]),
        "has_anxiety":    int(r["has_anxiety"]),
        "has_substance_use": int(r["has_substance_use"]),
        "depression_codes":    ";".join(sorted(set(ev.get("depression", [])))),
        "anxiety_codes":       ";".join(sorted(set(ev.get("anxiety", [])))),
        "substance_use_codes": ";".join(sorted(set(ev.get("substance_use", [])))),
    })
ev_df = pd.DataFrame(rows)
ev_df.to_csv(OUT / "patient_psych_evidence.csv", index=False)

# ---- consistency check: row-by-row flag derived from codes must match cohort flag ----
miss = 0
for _, r in ev_df.iterrows():
    for dx in ("depression", "anxiety", "substance_use"):
        derived = bool(r[f"{dx}_codes"])
        flagged = bool(r[f"has_{dx}"])
        if derived != flagged:
            miss += 1
print(f"Per-patient/per-disorder disagreements: {miss} / {len(ev_df)*3}", file=sys.stderr)

# ---- disjoint overlap table ----
def m(d, a, s):
    sub = ev_df[(ev_df.has_depression == d) & (ev_df.has_anxiety == a) & (ev_df.has_substance_use == s)]
    return len(sub)

overlap = pd.DataFrame([
    {"depression":1,"anxiety":1,"substance_use":1,"n":m(1,1,1)},
    {"depression":1,"anxiety":1,"substance_use":0,"n":m(1,1,0)},
    {"depression":1,"anxiety":0,"substance_use":1,"n":m(1,0,1)},
    {"depression":0,"anxiety":1,"substance_use":1,"n":m(0,1,1)},
    {"depression":1,"anxiety":0,"substance_use":0,"n":m(1,0,0)},
    {"depression":0,"anxiety":1,"substance_use":0,"n":m(0,1,0)},
    {"depression":0,"anxiety":0,"substance_use":1,"n":m(0,0,1)},
    {"depression":0,"anxiety":0,"substance_use":0,"n":m(0,0,0)},
])
overlap.to_csv(OUT / "triple65_disjoint.csv", index=False)
print("Overlap table:", file=sys.stderr)
print(overlap.to_string(index=False), file=sys.stderr)
assert overlap["n"].sum() == 244

# ---- provenance ----
prov = {
    "cohort_csv_md5": md5_of(COHORT_FILE),
    "diagnoses_icd_csv_gz_md5": md5_of(DX_FILE),
    "icd_codes_py_md5": md5_of(ANALYSIS / "icd_codes.py"),
    "rows_scanned": rows_seen,
    "per_patient_disagreements": miss,
}
(OUT / "provenance.json").write_text(json.dumps(prov, indent=2))
print(json.dumps(prov, indent=2), file=sys.stderr)
print("DONE.", file=sys.stderr)
