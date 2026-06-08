# Psychiatric Comorbidity in Epilepsy Surgery: Reproducibility Code

Analysis code for the study *"Prevalence and Postoperative Trajectory of
Psychiatric Comorbidities Among Patients Undergoing Epilepsy Surgery: A
Multi-Cohort Study."*

This repository contains code only: every script, the ICD code definitions, the
statistical pipeline, tests, and documentation needed to reproduce the analyses
from the source databases. **It contains no patient-level data.** The clinical
datasets (MIMIC-IV, NIS, and the MGB chart review) are obtained separately under
their respective data use agreements; see [`DATA_ACCESS.md`](DATA_ACCESS.md).

## What this study did

Three complementary cohorts were analyzed within one framework:

| Cohort | Source | Surgical n | Role |
|---|---|---|---|
| **MGB** | Mass General Brigham chart review (2005–2024) | 273 | Prevalence + postoperative trajectory (PHQ-9/GAD-7) |
| **MIMIC-IV v3.1** | BIDMC EHR (PhysioNet) | 244 / 8,968 | Surgical vs non-surgical, propensity-score matching |
| **NIS** | HCUP National Inpatient Sample (2012–2020) | 3,675 | Nationally representative trends |

Headline finding: **approximately half** of epilepsy-surgery patients carry at
least one psychiatric diagnosis; comorbidity decreases modestly after surgery,
with seizure freedom the strongest predictor of improvement.

## The "Triple65" result

In MIMIC-IV, depression, anxiety, and substance-use disorder each affect exactly
65 of 244 surgical patients (26.6%). The identical prevalence is real, not a bug:
the three groups are different patients. The full audit, including four
independent re-derivations from the raw records, is in
[`docs/TRIPLE65_EXPLAINER.md`](docs/TRIPLE65_EXPLAINER.md). Check it yourself:

```bash
export MIMIC_ROOT=/path/to/physionet.org/files/mimiciv/3.1
python src/mimic/verify_triple65_duckdb.py   # independent DuckDB re-derivation
```

## Repository layout

```
src/common/icd_codes.py      Single source of truth for all ICD-9/10 code lists
src/mimic/                   MIMIC-IV cohort build, PSM, regression, evidence/Sankey builders
src/nis/                     NIS import + survey-weighted analysis
src/mgb/                     MGB pipeline: build_mgb_analysis_dataset (bracket-aware
                             PHQ-9/GAD-7 parse + coalesced baseline), recompute_b11_b13_final
                             (MCID improvement, paired-vs-unpaired, trajectory), make_b11_b13_figures
tests/                       Invariant + ICD-matching unit tests
docs/                        Architecture, line-by-line internals, Triple65 explainer, ADRs
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest                       # runs invariant checks that do not need patient data
```

Analyses that require the clinical databases are gated on the environment
variables documented in [`DATA_ACCESS.md`](DATA_ACCESS.md).

## Documentation

- [`docs/architecture.md`](docs/architecture.md): pipeline data-flow
- [`docs/CODE_INTERNALS.md`](docs/CODE_INTERNALS.md): a from-scratch, line-by-line walkthrough of the code for readers new to Python
- [`docs/TRIPLE65_EXPLAINER.md`](docs/TRIPLE65_EXPLAINER.md): the identical-prevalence audit
- [`docs/adr/`](docs/adr/): architecture decision records

## Author

Niels Pacheco-Barrios, MD. Code released under the [MIT License](LICENSE).
The study itself is the work of the full author team (see the manuscript and
[`CITATION.cff`](CITATION.cff)).
