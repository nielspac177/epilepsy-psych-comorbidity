# 0001. One file defines every ICD code list

Status: accepted

## Context

The study counts psychiatric diagnoses across three datasets (MIMIC-IV, NIS, and
the MGB chart review). Every count depends on which ICD codes are treated as
depression, anxiety, substance use, and so on. If each dataset's pipeline defined
those code lists on its own, the three could drift apart, and the cross-dataset
comparison that is the point of the paper would quietly stop comparing like with
like. A reviewer would also have to hunt through several files to audit the
definitions.

## Decision

All ICD-9 and ICD-10 code definitions live in a single file,
`src/common/icd_codes.py`. Every pipeline imports its definitions from there. No
script defines a disorder locally.

## Consequences

A reviewer can audit the entire study's case definitions by reading one short
file. Changing a definition changes it everywhere at once, which removes a whole
class of "the numbers don't add up between sections" bugs. The cost is a small
amount of coupling: the three pipelines all depend on this one module, which is
the intended trade.
