# Architecture Decision Records

These short records capture the decisions that shaped how this analysis is built,
along with the reasoning behind them, so that a future reader (or reviewer) can
see not just what the code does but why it was set up this way.

Each record follows the same shape: the context that forced a choice, the
decision, and the consequences that followed.

| # | Decision |
|---|----------|
| [0001](0001-single-source-of-truth-for-icd-codes.md) | One file defines every ICD code list |
| [0002](0002-code-only-public-repo.md) | Public repo holds code only; data lives elsewhere |
| [0003](0003-patient-level-prefix-matching.md) | Disorders are flagged by patient-level ICD prefix matching |
| [0004](0004-independent-reverification.md) | Headline results are re-derived by independent code paths |
