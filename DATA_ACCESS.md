# Data access

This repository ships **no patient-level data**. Reproducing the analyses
requires obtaining each dataset under its own agreement.

## MIMIC-IV v3.1 (BIDMC EHR)

Credentialed access via PhysioNet: https://physionet.org/content/mimiciv/3.1/

The MIMIC data use agreement **prohibits redistribution** of the patient-level
data. We therefore do not include `diagnoses_icd.csv.gz`, the cohort CSVs, or any
per-patient evidence file in this public repository. After you obtain MIMIC-IV:

```bash
export MIMIC_ROOT=/path/to/physionet.org/files/mimiciv/3.1
```

Scripts read `hosp/diagnoses_icd.csv.gz`, `hosp/procedures_icd.csv.gz`, and the
derived cohort file `analysis/epilepsy_psych/epilepsy_patient_cohort_psm.csv`.

To confirm you are using the exact same inputs we did, check these MD5s:

| File | MD5 |
|---|---|
| `hosp/diagnoses_icd.csv.gz` | `53535040f59bd4f2a68de9c9c04876f1` |
| `epilepsy_patient_cohort_psm.csv` | `6fec977f756603fc3f380b560e367a34` |

## NIS — HCUP National Inpatient Sample (2012–2020)

Purchased/licensed through the HCUP Central Distributor:
https://hcup-us.ahrq.gov/. Redistribution is not permitted. Set:

```bash
export NIS_ROOT=/path/to/NIS
```

## MGB chart-review cohort

IRB-approved Mass General Brigham data. Not publicly shareable. The analysis
code (`src/mgb/`) runs against the institutional extract; column expectations are
documented in each script.

## Patient-level derived files (private)

Per-patient evidence tables (e.g. ICD codes contributing to each flag) used to
satisfy reviewer audit requests live in a **separate private repository**
restricted to credentialed collaborators, never in this public repo. A branch in
a public repo is world-readable, so "private branch" is not a safe option for
credentialed data — a separate private repository is used instead.
