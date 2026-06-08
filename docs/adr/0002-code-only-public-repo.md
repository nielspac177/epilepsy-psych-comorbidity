# 0002. Public repo holds code only; data lives elsewhere

Status: accepted

## Context

The analysis runs on three restricted datasets. MIMIC-IV is credentialed
PhysioNet data whose use agreement forbids passing it to third parties, which
includes uploading it to GitHub even in a private repository. The NIS is licensed
through HCUP. The MGB chart review contains direct identifiers and is governed by
institutional review board approval and HIPAA. At the same time, the work needs to
be reproducible and open to inspection.

## Decision

This public repository contains code, code-list definitions, tests, and
documentation, and no patient-level data of any kind. A `.gitignore` blocks data
files, and the continuous-integration job fails if any data file is ever tracked.
Patient-level derived files (for example, the per-patient ICD evidence used to
answer audit requests) live in a separate private repository limited to
credentialed collaborators. Anyone reproducing the work obtains the source data
under the appropriate agreement and runs the code against it.

## Consequences

The reproducibility goal and the data agreements are both satisfied without
compromise. Reproduction takes one extra step (obtaining the data), which is
unavoidable for restricted data and is documented in `DATA_ACCESS.md`. A "private
branch" inside this public repo was rejected, because every branch of a public
repository is world-readable, so a separate private repository is used instead.
