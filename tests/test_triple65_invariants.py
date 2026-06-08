"""
Invariant test for the Triple65. Skipped automatically unless MIMIC_ROOT points
at a local MIMIC-IV v3.1 install (the data cannot be redistributed). When the
data is present, this re-derives the result from raw and asserts the invariants
that make the result trustworthy.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HAS_MIMIC = bool(os.environ.get("MIMIC_ROOT")) and Path(
    os.environ.get("MIMIC_ROOT", "")
).joinpath("hosp/diagnoses_icd.csv.gz").exists()

pytestmark = pytest.mark.skipif(not HAS_MIMIC, reason="MIMIC_ROOT not set / data absent")


def test_duckdb_rederivation_passes():
    """verify_triple65_duckdb exits 0 only on 65/65/65 with 0 disagreements."""
    r = subprocess.run(
        [sys.executable, str(ROOT / "src" / "mimic" / "verify_triple65_duckdb.py")],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "65" in r.stdout and "PASS" in r.stdout


def test_disjoint_table_sums_to_244():
    import csv
    out = ROOT / "verification_out" / "triple65_disjoint_duckdb.csv"
    assert out.exists(), "run verify_triple65_duckdb.py first"
    with open(out) as f:
        rows = list(csv.DictReader(f))
    assert sum(int(r["n"]) for r in rows) == 244
    # marginals all equal 65
    dep = sum(int(r["n"]) for r in rows if r["depression"] == "1")
    anx = sum(int(r["n"]) for r in rows if r["anxiety"] == "1")
    sub = sum(int(r["n"]) for r in rows if r["substance_use"] == "1")
    assert dep == anx == sub == 65
