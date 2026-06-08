# 0003. Disorders are flagged by patient-level ICD prefix matching

Status: accepted

## Context

A patient can have many hospital admissions and many diagnosis codes per
admission. ICD codes are also hierarchical: `F32` is a family of depression codes
with many specific members (`F320`, `F321`, and so on). We had to decide how to
turn raw diagnosis records into a yes or no answer for each disorder, and at what
level to count.

## Decision

A disorder is flagged using prefix matching: a code counts if it starts with any
of the disorder's listed prefixes, so one short prefix covers a whole code family.
Flags are assigned at the patient level: a patient is positive for a disorder if
any of their diagnosis records matches, counted once regardless of how many
records or admissions match. The prefix lists for the three main disorders are
kept mutually exclusive, so no single code can be counted toward two disorders.

## Consequences

The code-list definitions stay short and readable while still covering every
member of each ICD family. Patient-level counting answers the clinically
meaningful question (how many people have the disorder) rather than how many
diagnosis lines mention it; the two differ substantially, and using admission-level
counting would change the headline numbers. The disjoint prefix lists are what make
it impossible for the three main disorders to share a patient through a
double-counted code, a property the tests check directly.
