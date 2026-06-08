# Psychiatric Comorbidities in Epilepsy: Surgical vs. Non-Surgical Patients

## Study Overview
**Objective:** Determine the prevalence of DSM-5 Axis I psychiatric disorders in epilepsy patients, comparing those who underwent epilepsy surgery vs. non-surgical epilepsy patients, using MIMIC-IV.

## Research Questions
1. What is the overall prevalence of psychiatric comorbidities among hospitalized epilepsy patients?
2. Is the prevalence different in epilepsy surgery patients vs. non-surgical epilepsy patients?
3. What are the demographic and clinical characteristics associated with psychiatric comorbidity?

## Study Design
- **Data source:** MIMIC-IV v3.1 (single academic medical center: BIDMC)
- **Study population:** All admissions with an epilepsy diagnosis (ICD-9: 345.x; ICD-10: G40.x)
- **Exposure:** Epilepsy surgery (identified by procedure codes)
- **Outcomes:** Prevalence of psychiatric diagnoses (depression, bipolar, anxiety, PTSD, psychosis, OCD, ADHD, substance use disorders)
- **Covariates:** Age, sex, race, insurance, Charlson comorbidity index

## Limitations
- Single-center study (vs. NIS nationwide)
- Administrative coding may underestimate psychiatric prevalence
- MIMIC over-represents ICU patients
- Cannot determine temporality (pre-existing vs. new-onset psychiatric disease)

## Files
- `01_cohort_identification.ipynb` — Identify epilepsy patients and surgical subcohort
- `icd_codes.py` — ICD-9 and ICD-10 code definitions
- `README.md` — This file
