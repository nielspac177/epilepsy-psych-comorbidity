# Code review log

Every script in this repository is reviewed before publication against the
`code-review-excellence` checklist (correctness, security/DUA leakage,
performance, maintainability, tests). Severity labels: 🔴 blocking · 🟡 important
· 🟢 nit · 💡 suggestion · 🎉 praise.

## DUA leak check (applies to the whole repo) — 🔴→resolved

- **Risk:** committing credentialed MIMIC/NIS/MGB patient-level data to a public
  repo violates the data use agreement.
- **Controls:** `.gitignore` excludes `data/`, `verification_out/`, all `*.csv`/
  `*.xlsx`/`*.db`, `subject_flags.txt`, `surgical_ids.txt`, and `*evidence*`/
  `*cohort*` files. Per-patient builders (`build_evidence*.py`) write only to
  ignored paths. **Verified:** `git ls-files` carries no data file; aggregate
  tables embedded in docs contain counts only, no identifiers.

## New verification scripts (authored for this audit)

### `src/mimic/verify_triple65_duckdb.py` — ✅ approve
- 🎉 Independent SQL re-derivation; version-aware prefix matching; asserts
  n_surgical==244; re-adds zero-diagnosis patients so all 244 are counted;
  emits MD5 provenance; exit code encodes the invariant.
- 🟢 `LIKE 'F32%'` assumes no leading whitespace in `icd_code`; MIMIC codes are
  clean, and the pandas/shell re-derivations strip whitespace and agree, so this
  is non-blocking.

### `src/mimic/coincidence_math.py` — ✅ approve
- 🎉 Computes the correct coincidence model (binomial convolution) under common
  and heterogeneous rates; independently reproduced by the workflow statistician
  agent to the same values (0.0019 / 0.00077).
- 💡 Could expose `p` and the heterogeneous rates as CLI args for sensitivity.

### `src/mgb/parse_phq_gad.py` — ✅ approve with caveats documented
- 🎉 Bracket-aware parser recovers follow-up scores (`[13]`, `0 (Phq4score)`)
  that naive `to_numeric` dropped — the root cause of the lossy
  `merged_deprivation` file.
- 🟡 Pre/post timepoint mapping is genuinely ambiguous in the source; the script
  reports every plausible mapping rather than hard-coding one. Documented as a
  data-provenance flag, not a code defect.

## Legacy pipeline scripts (packaged as-run for transparency)

`build_evidence*.py`, `03_psm_analysis.py`, `09_logreg_full.py`, etc. are
included verbatim as the code that produced the manuscript, then reviewed:
- 🎉 `build_evidence.py` re-derives flags from raw and asserts 0 disagreements —
  a built-in self-audit.
- 🟡 Hard-coded absolute data paths → should move to `MIMIC_ROOT`/`NIS_ROOT` env
  vars (tracked as a follow-up; does not affect correctness).
- 🟢 `DataFrame.iterrows()` in the evidence builders is slow but correct at this
  cohort size; vectorization is a future optimization.

## Verdict
All scripts approved for the public (code-only) repository. High-risk files
(cohort filtering, ICD matching, PSM) were additionally cross-reviewed by the
adversarial refuter agents, which failed to break the Triple65 result.
