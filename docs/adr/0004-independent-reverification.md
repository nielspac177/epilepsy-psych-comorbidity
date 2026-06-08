# 0004. Headline results are re-derived by independent code paths

Status: accepted

## Context

The most scrutinized result in the study is that depression, anxiety, and
substance-use disorder each affect exactly 65 of 244 surgical patients in
MIMIC-IV. Three identical counts look like a bug, and a single script confirming
its own output proves little: if the script has an error, the error is in the
answer too.

## Decision

The headline result is re-derived from the raw records by separate
implementations that share no code: a DuckDB SQL query, a streaming pandas script,
and a shell-and-awk pipeline, checked against the cohort file's own stored flags.
The re-derived per-patient flags are compared against the stored flags, and the
verification script only reports success if the counts are right and zero patients
disagree. A small set of adversarial checks deliberately tries to break the result
(prefix over-reach, version confusion, admission-versus-patient counting, join
errors).

## Consequences

Agreement across methods that share no code is strong evidence that the result is
real rather than an artifact of one implementation. The approach costs extra code
and runtime that a single pipeline would not, which is justified here because the
result is central to the paper and was specifically challenged in review. The same
pattern is available for any future result that draws similar scrutiny. The full
write-up is in `docs/TRIPLE65_EXPLAINER.md`.
