#!/usr/bin/env python3
"""
Independent re-derivation of the MIMIC-IV "Triple65" using a DuckDB/SQL code
path that shares NO code with the original pandas builder (build_evidence.py).

Purpose (reviewer concern, Dr. Rolston): confirm that depression, anxiety, and
substance-use disorder each affect exactly 65/244 surgical epilepsy patients,
that these are *different* patients (not a copy/paste artifact), and that flags
re-derived from raw ICD records exactly match the stored cohort flags.

Run:
    python src/mimic/verify_triple65_duckdb.py

Inputs (MIMIC-IV v3.1, credentialed PhysioNet data -- NOT redistributed):
    $MIMIC_ROOT/hosp/diagnoses_icd.csv.gz
    $MIMIC_ROOT/analysis/epilepsy_psych/epilepsy_patient_cohort_psm.csv

Outputs (verification_out/):
    triple65_marginals.json      derived marginals + disagreement count
    triple65_disjoint_duckdb.csv 8-row overlap table

Exit code 0 only if 65/65/65 reproduces AND derived==stored for every patient.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import duckdb

# --- paths ------------------------------------------------------------------
MIMIC_ROOT = Path(
    os.environ.get(
        "MIMIC_ROOT",
        "/Volumes/Niels 2/MIMIC/physionet.org/files/mimiciv/3.1",
    )
)
DX_FILE = MIMIC_ROOT / "hosp" / "diagnoses_icd.csv.gz"
COHORT_FILE = MIMIC_ROOT / "analysis" / "epilepsy_psych" / "epilepsy_patient_cohort_psm.csv"
OUT = Path(__file__).resolve().parents[2] / "verification_out"
OUT.mkdir(exist_ok=True)

# --- ICD prefix definitions (verbatim from analysis/epilepsy_psych/icd_codes.py) ---
PSY = {
    "depression":    {"icd10": ["F32", "F33", "F341"],
                      "icd9":  ["2962", "2963", "3004", "311"]},
    "anxiety":       {"icd10": ["F40", "F41"],
                      "icd9":  ["30000", "30001", "30002", "30021", "30022", "30023", "30029"]},
    "substance_use": {"icd10": ["F10", "F11", "F12", "F13", "F14", "F15", "F16",
                                "F17", "F18", "F19"],
                      "icd9":  ["303", "304", "305"]},
}


def md5_of(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(8 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sql_flag(dx: str) -> str:
    """Build a SQL boolean: does any ICD code (version-aware) match this disorder?"""
    v10 = " OR ".join(f"icd_code LIKE '{p}%'" for p in PSY[dx]["icd10"])
    v9 = " OR ".join(f"icd_code LIKE '{p}%'" for p in PSY[dx]["icd9"])
    return f"MAX(CASE WHEN (icd_version = 10 AND ({v10})) " \
           f"OR (icd_version = 9 AND ({v9})) THEN 1 ELSE 0 END)"


def main() -> int:
    for f in (DX_FILE, COHORT_FILE):
        if not f.exists():
            sys.exit(f"Missing input: {f}\nSet MIMIC_ROOT to your local MIMIC-IV v3.1 path.")

    con = duckdb.connect()
    con.execute(f"CREATE VIEW cohort AS SELECT * FROM read_csv_auto('{COHORT_FILE.as_posix()}')")
    con.execute(
        f"CREATE VIEW dx AS SELECT subject_id, CAST(icd_version AS INT) icd_version, "
        f"CAST(icd_code AS VARCHAR) icd_code "
        f"FROM read_csv_auto('{DX_FILE.as_posix()}', compression='gzip')"
    )

    n_surg = con.execute("SELECT count(*) FROM cohort WHERE surgical = 1").fetchone()[0]
    assert n_surg == 244, f"expected 244 surgical, got {n_surg}"

    # Re-derive disorder flags for surgical patients straight from raw ICD rows.
    con.execute(
        f"""
        CREATE TABLE derived AS
        SELECT c.subject_id,
               {sql_flag('depression')}    AS dep,
               {sql_flag('anxiety')}        AS anx,
               {sql_flag('substance_use')}  AS sub
        FROM cohort c
        JOIN dx ON dx.subject_id = c.subject_id
        WHERE c.surgical = 1
        GROUP BY c.subject_id
        """
    )
    # Patients with zero diagnosis rows would be dropped by the JOIN; re-add as all-zero.
    con.execute(
        """
        INSERT INTO derived
        SELECT c.subject_id, 0, 0, 0 FROM cohort c
        WHERE c.surgical = 1 AND c.subject_id NOT IN (SELECT subject_id FROM derived)
        """
    )

    marg = con.execute("SELECT sum(dep), sum(anx), sum(sub), count(*) FROM derived").fetchone()
    dep, anx, sub, n = marg
    disjoint = con.execute(
        """
        SELECT dep AS depression, anx AS anxiety, sub AS substance_use, count(*) AS n
        FROM derived GROUP BY dep, anx, sub
        ORDER BY depression DESC, anxiety DESC, substance_use DESC
        """
    ).fetchdf()

    # Compare re-derived flags against the stored cohort flags, patient by patient.
    disagree = con.execute(
        """
        SELECT count(*) FROM derived d
        JOIN cohort c ON c.subject_id = d.subject_id
        WHERE d.dep <> c.has_depression
           OR d.anx <> c.has_anxiety
           OR d.sub <> c.has_substance_use
        """
    ).fetchone()[0]

    result = {
        "code_path": "duckdb-sql (independent of build_evidence.py pandas path)",
        "n_surgical": int(n),
        "depression": int(dep),
        "anxiety": int(anx),
        "substance_use": int(sub),
        "all_three_equal_65": bool(dep == anx == sub == 65),
        "per_patient_disagreements_vs_stored_flags": int(disagree),
        "inputs_md5": {
            "diagnoses_icd_csv_gz": md5_of(DX_FILE),
            "cohort_csv": md5_of(COHORT_FILE),
        },
    }
    disjoint.to_csv(OUT / "triple65_disjoint_duckdb.csv", index=False)
    (OUT / "triple65_marginals.json").write_text(json.dumps(result, indent=2))

    print(json.dumps(result, indent=2))
    print("\nDisjoint overlap table (independent DuckDB derivation):")
    print(disjoint.to_string(index=False))

    ok = result["all_three_equal_65"] and disagree == 0
    print("\nVERDICT:", "PASS — 65/65/65 reproduced, 0 disagreements" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
