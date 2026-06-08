"""
Pure-logic tests for the ICD prefix definitions. These run WITHOUT any
patient-level data and guard the single source of truth in
src/common/icd_codes.py against accidental edits that would change cohort
membership.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "common"))
import icd_codes as ic  # noqa: E402

PSY = ic.PSYCH_CATEGORIES


def matches(code: str, version: int, disorder: str) -> bool:
    prefixes = PSY[disorder]["icd10"] if version == 10 else PSY[disorder]["icd9"]
    return any(str(code).startswith(p) for p in prefixes)


def test_known_codes_classify_correctly():
    assert matches("F329", 10, "depression")     # MDD
    assert matches("F411", 10, "anxiety")         # generalized anxiety
    assert matches("F1020", 10, "substance_use")  # alcohol dependence
    assert matches("311", 9, "depression")        # depressive disorder NOS
    assert matches("30000", 9, "anxiety")
    assert matches("3050", 9, "substance_use")


def test_three_main_disorders_have_disjoint_code_sets():
    # The Triple65 audit relies on depression/anxiety/substance being built from
    # mutually exclusive prefix sets, so no code can be double-counted.
    for v in ("icd9", "icd10"):
        dep = set(PSY["depression"][v])
        anx = set(PSY["anxiety"][v])
        sub = set(PSY["substance_use"][v])
        assert dep.isdisjoint(anx)
        assert dep.isdisjoint(sub)
        assert anx.isdisjoint(sub)


def test_depression_prefix_does_not_leak_into_anxiety():
    # ICD-9 '3004' (dysthymia) must not prefix-match any anxiety code (300.0x).
    for anx_code in PSY["anxiety"]["icd9"]:
        assert not anx_code.startswith("3004")


def test_substance_use_covers_f10_through_f19():
    for i in range(10, 20):
        assert f"F{i}" in PSY["substance_use"]["icd10"]


def test_epilepsy_codes_present():
    assert "G40" in ic.EPILEPSY_ICD10
    assert "345" in ic.EPILEPSY_ICD9
