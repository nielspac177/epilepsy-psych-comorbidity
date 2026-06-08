#!/usr/bin/env python3
"""Independent re-derivation of MIMIC Triple65 using pure pandas.

Reads diagnoses_icd.csv.gz in chunks, applies version-aware prefix matching
via str.startswith, aggregates per subject_id with groupby, then intersects
with the surgical cohort and reports marginal + disjoint overlap counts.
"""
import pandas as pd
from itertools import product

DIAG = "/Volumes/Niels 2/MIMIC/physionet.org/files/mimiciv/3.1/hosp/diagnoses_icd.csv.gz"
COHORT = "/Volumes/Niels 2/MIMIC/physionet.org/files/mimiciv/3.1/analysis/epilepsy_psych/epilepsy_patient_cohort_psm.csv"

CODES = {
    "depression": {
        10: ("F32", "F33", "F341"),
        9:  ("2962", "2963", "3004", "311"),
    },
    "anxiety": {
        10: ("F40", "F41"),
        9:  ("30000", "30001", "30002", "30021", "30022", "30023", "30029"),
    },
    "substance_use": {
        10: ("F10", "F11", "F12", "F13", "F14", "F15", "F16", "F17", "F18", "F19"),
        9:  ("303", "304", "305"),
    },
}

DISORDERS = ["depression", "anxiety", "substance_use"]

# Per-subject flags accumulated across chunks
flags = {d: set() for d in DISORDERS}

reader = pd.read_csv(
    DIAG,
    compression="gzip",
    usecols=["subject_id", "icd_code", "icd_version"],
    dtype={"subject_id": "int64", "icd_code": "object", "icd_version": "int64"},
    chunksize=500_000,
)

for chunk in reader:
    code = chunk["icd_code"].str.strip()
    v9 = chunk["icd_version"] == 9
    v10 = chunk["icd_version"] == 10
    for d in DISORDERS:
        pref10 = CODES[d][10]
        pref9 = CODES[d][9]
        m = (v10 & code.str.startswith(pref10)) | (v9 & code.str.startswith(pref9))
        # str.startswith with a tuple works on python str; for pandas StringArray
        # we apply per-prefix OR below to be safe.
        flags[d].update(chunk.loc[m.fillna(False), "subject_id"].tolist())

# Load cohort and restrict to surgical
cohort = pd.read_csv(COHORT)
surgical = cohort[cohort["surgical"] == 1].copy()
n_surgical = len(surgical)

for d in DISORDERS:
    surgical[d] = surgical["subject_id"].isin(flags[d]).astype(int)

marg = {d: int(surgical[d].sum()) for d in DISORDERS}

# Disjoint overlap
print("n_surgical =", n_surgical)
print("marginals  =", marg)
print("disjoint (dep,anx,sub,n):")
for dep, anx, sub in product((1, 0), repeat=3):
    n = int(((surgical["depression"] == dep) &
             (surgical["anxiety"] == anx) &
             (surgical["substance_use"] == sub)).sum())
    print(f"  ({dep},{anx},{sub},{n})")
