# Architecture

The study runs three independent cohort pipelines that converge on a common set
of psychiatric-comorbidity definitions (`src/common/icd_codes.py`).

## Data flow

```mermaid
flowchart TD
    subgraph CODES["Single source of truth"]
        ICD["src/common/icd_codes.py<br/>ICD-9/10 prefix lists:<br/>epilepsy, surgery, 11 psych categories"]
    end

    subgraph MIMIC["MIMIC-IV v3.1 pipeline (src/mimic)"]
        M1["diagnoses_icd.csv.gz<br/>procedures_icd.csv.gz"]
        M2["01_cohort_identification<br/>→ epilepsy_patient_cohort_psm.csv<br/>(8,968 patients, 244 surgical)"]
        M3["03_psm_analysis<br/>1:1 propensity matching"]
        M4["09_logreg_full<br/>multivariable models"]
        M5["build_evidence / build_sankey<br/>per-patient ICD evidence (PRIVATE)"]
        M6["verify_triple65_duckdb<br/>coincidence_math<br/>rederive_pandas / rederive_shell"]
        M1 --> M2 --> M3 --> M4
        M2 --> M5
        M2 --> M6
    end

    subgraph NIS["NIS pipeline (src/nis)"]
        N1["NIS ASCII (2012–2020)"]
        N2["import_nis → DuckDB"]
        N3["NIS_Analysis<br/>survey-weighted trends"]
        N1 --> N2 --> N3
    end

    subgraph MGB["MGB pipeline (src/mgb)"]
        G1["IRB chart-review extract"]
        G2["parse_phq_gad<br/>(bracket-aware PHQ-9/GAD-7)"]
        G3["symptom trajectory<br/>MCID improvement, paired-vs-unpaired"]
        G1 --> G2 --> G3
    end

    ICD --> M2
    ICD --> N3
    ICD --> G3

    M4 --> R["Manuscript tables/figures<br/>+ reviewer-response artifacts"]
    N3 --> R
    G3 --> R
    M6 --> R
```

## Design principles

- **One source of truth for codes.** Every pipeline imports the same prefix
  lists from `src/common/icd_codes.py`. No cohort redefines a disorder locally.
- **Patient-level data never enters the public repo.** Builders that emit
  per-patient evidence write to paths excluded by `.gitignore`; the public repo
  carries only code and fully aggregated tables.
- **Independent verifiability.** The headline MIMIC result is re-derivable by
  three separate implementations (DuckDB SQL, streaming pandas, shell/awk) that
  share no code — see `docs/TRIPLE65_EXPLAINER.md`.
- **Ascertainment differs by cohort by design.** MIMIC-IV aggregates diagnoses
  across all admissions (cumulative); NIS treats each discharge independently
  (single-encounter); MGB adds chart review and PHQ-9/GAD-7. These differences
  are intrinsic to the data and are surfaced, not hidden, in the results.
```
