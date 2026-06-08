# Code internals — a line-by-line walkthrough

This document explains the analysis pipeline from the top down: first the
architecture, then a script-by-script, often line-by-line, reading of the code
that matters most. It is written so that a reader who knows basic Python but not
this codebase can follow exactly how a row in `diagnoses_icd.csv.gz` becomes a
number in the manuscript.

Read [`architecture.md`](architecture.md) first for the data-flow diagram.

---

## Part 0 — The mental model

Every cohort answers one question: *for each patient, which psychiatric
disorders are present?* The answer is always built the same way:

1. Define a cohort (a set of `subject_id`s).
2. Stream the diagnosis records.
3. For each record, test its ICD code against a fixed list of **prefixes**.
4. A patient "has" a disorder if **any** of their records matches.

Everything else — propensity matching, regression, the Triple65 audit — sits on
top of that one operation. The prefix lists live in exactly one file.

---

## Part 1 — `src/common/icd_codes.py` (the single source of truth)

```python
EPILEPSY_ICD10 = {"G40": "Epilepsy and recurrent seizures (all subtypes)"}
EPILEPSY_ICD9  = {"345": "Epilepsy and recurrent seizures (all subtypes)"}
```

These are **prefix** keys, not exact codes. `"G40"` matches `G40.001`,
`G40.219`, etc., because matching is done with `str.startswith`. One key
therefore covers an entire ICD family. The dict *value* is documentation only.

```python
PSYCH_CATEGORIES = {
    "depression": {
        "label": "Depressive Disorders",
        "icd10": ["F32", "F33", "F341"],
        "icd9":  ["2962", "2963", "3004", "311"],
    },
    ...
}
```

Each disorder carries an ICD-10 list and an ICD-9 list, kept separate because
the two coding systems are matched against **different** record subsets (by the
`icd_version` column). Two design choices here are load-bearing for the whole
study:

- **`F341` not `F34`.** The depression list includes `F341` (dysthymia) but not
  the bare `F34`, so it cannot accidentally swallow `F340` (cyclothymia, a
  *bipolar* code). This precision is what the Triple65 prefix-overreach refuter
  tested and confirmed.
- **The three main disorders use disjoint prefixes.** `depression`, `anxiety`,
  and `substance_use` share no prefix, so no single diagnosis code can increment
  two disorders. `tests/test_icd_matching.py` asserts this disjointness, which is
  why the 65/65/65 totals cannot be a double-counting artifact.

---

## Part 2 — `src/mimic/verify_triple65_duckdb.py` (independent re-derivation)

The purpose of this file is to recompute the headline MIMIC result with code
that shares nothing with the original pandas builder. Walking the important
lines:

```python
MIMIC_ROOT = Path(os.environ.get("MIMIC_ROOT", "/Volumes/.../mimiciv/3.1"))
```

The data path comes from an environment variable so the script is portable; the
default is only a local convenience. No data is embedded.

```python
def sql_flag(dx: str) -> str:
    v10 = " OR ".join(f"icd_code LIKE '{p}%'" for p in PSY[dx]["icd10"])
    v9  = " OR ".join(f"icd_code LIKE '{p}%'" for p in PSY[dx]["icd9"])
    return f"MAX(CASE WHEN (icd_version = 10 AND ({v10})) " \
           f"OR (icd_version = 9 AND ({v9})) THEN 1 ELSE 0 END)"
```

This builds a SQL expression dynamically from the prefix lists. `LIKE 'F32%'` is
the SQL equivalent of `startswith("F32")`. The `CASE` is **version-aware**: an
ICD-10 row is only tested against the ICD-10 prefixes and vice versa. Wrapping it
in `MAX(... ) ... GROUP BY subject_id` collapses many diagnosis rows per patient
into a single 0/1 flag — this is the patient-level aggregation, expressed as one
SQL idiom.

```python
n_surg = con.execute("SELECT count(*) FROM cohort WHERE surgical = 1").fetchone()[0]
assert n_surg == 244, f"expected 244 surgical, got {n_surg}"
```

A guard: if the cohort file ever changes shape, the script fails loudly instead
of silently producing the wrong denominator.

```python
INSERT INTO derived
SELECT c.subject_id, 0, 0, 0 FROM cohort c
WHERE c.surgical = 1 AND c.subject_id NOT IN (SELECT subject_id FROM derived)
```

A subtle correctness point: the `JOIN` to diagnoses drops any surgical patient
who happens to have **zero** diagnosis rows. This statement re-adds them as
all-zero so the denominator stays exactly 244. (The cohort-join refuter checked
precisely this failure mode.)

```python
disagree = con.execute(""" ... WHERE d.dep <> c.has_depression OR ... """).fetchone()[0]
```

The script does not trust its own recomputation in isolation: it compares the
re-derived flags against the cohort's stored flags, patient by patient, and the
exit code requires `disagree == 0`. That is the self-audit.

---

## Part 3 — `src/mimic/coincidence_math.py` (how surprising is 65/65/65?)

```python
def p_all_three_equal_anything(p1, p2, p3, n=244):
    k = np.arange(0, n + 1)
    pmf1, pmf2, pmf3 = binom.pmf(k, n, p1), binom.pmf(k, n, p2), binom.pmf(k, n, p3)
    return float(np.sum(pmf1 * pmf2 * pmf3))
```

This is the entire statistical argument in four lines. For every possible shared
count `k` from 0 to 244, it multiplies the three binomial probabilities of
landing on `k` and sums them — i.e. P(all three counts are equal, to *anything*).
That is the correct model for "three numbers happened to match," as opposed to
P(all three hit one pre-specified value), which is what produces the
astronomically small figure the reviewer cited. The function is called with a
common rate and with the disorder-specific rates to show the answer (~0.2% /
~0.08%) is robust either way.

---

## Part 4 — `src/mimic/build_evidence.py` (the per-patient audit trail, original)

This is the original pipeline script, included verbatim. Its core loop:

```python
for chunk in pd.read_csv(DX_FILE, dtype={"icd_code": str}, chunksize=500_000):
    chunk = chunk[chunk["subject_id"].isin(surg_ids)]
    for _, r in chunk.iterrows():
        for dx in ("depression", "anxiety", "substance_use"):
            if matches(code, ver, dx):
                evidence[sid][dx].append(f"ICD-{ver}:{code}")
```

It streams the gzip in 500k-row chunks (so the 33 MB compressed / much larger
uncompressed file never has to fit in memory), keeps only surgical patients, and
records **every** ICD code that triggers each flag. The output
`patient_psych_evidence.csv` is what lets a reviewer see, for one `subject_id`,
exactly which diagnosis produced "has_depression = 1." The script then re-derives
the flags from those codes and asserts the disjoint overlap sums to 244 — another
built-in self-check. (This file emits patient-level data and therefore writes
only to a git-ignored path; it lives in the **private** data repo's outputs.)

---

## Part 5 — `src/mgb/parse_phq_gad.py` (why the merged CSV was wrong)

```python
def parse_score(x) -> float:
    if pd.isna(x): return np.nan
    s = str(x).strip().replace("[", "").replace("]", "")
    m = re.search(r"-?\d+\.?\d*", s)
    return float(m.group()) if m else np.nan
```

This four-line function is the fix for a real data bug. The source workbook
stores some follow-up scores as text in brackets (`"[13]"`) and one as
`"0 (Phq4score)"`. A naive `pd.to_numeric` returns `NaN` for all of these,
silently discarding ~30% of the follow-up PHQ-9/GAD-7 values — which is how an
earlier merge undercounted. `parse_score` strips the brackets and extracts the
first number, recovering them. The rest of the module reports paired counts under
**every** plausible pre/post column mapping rather than hard-coding one, because
the source's timepoint columns are genuinely ambiguous.

---

## Part 6 — The statistical layer (read at the file level)

These scripts are standard and best read directly; the key entry points:

- **`src/mimic/03_psm_analysis.py`** — 1:1 nearest-neighbor propensity-score
  matching (surgical vs non-surgical) on age, sex, ASM count, drug-resistant and
  focal codes, status-epilepticus history, and admission count. Produces the
  balance diagnostics behind eTable S2.
- **`src/mimic/06_balance_prepost.py`** — standardized-mean-difference balance
  table (the love plot).
- **`src/mimic/09_logreg_full.py`** — the full multivariable logistic regression
  (n = 8,968) reported in Figure 1; `10_psm_C_no_insurance.py` is the
  insurance-excluded sensitivity model (eTable S3).
- **`src/nis/import_nis.py` / `NIS_Analysis.ipynb`** — load the NIS ASCII files
  into DuckDB and run the survey-weighted trend models (accounting for discharge
  weights, strata, and hospital clustering).

Each imports its disorder definitions from `src/common/icd_codes.py`; none
redefines a code list locally. That single-source discipline is what makes the
cross-cohort numbers comparable and the whole pipeline auditable.
