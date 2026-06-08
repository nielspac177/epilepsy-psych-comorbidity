# Why three psychiatric diagnoses share the same prevalence in MIMIC-IV — and why that is correct, not a data error

**Scope.** This note explains a single, deliberately scrutinized result: in the
MIMIC-IV surgical epilepsy cohort, **depression, anxiety, and substance-use
disorder each affect exactly 65 of 244 patients (26.6%)**. At first glance an
identical prevalence for three different disorders looks like a copy/paste bug.
It is not. This document shows, with aggregate data only (no patient-level
information, in keeping with the PhysioNet MIMIC data use agreement), why the
result is real and how to reproduce it.

---

## 1. The observation

| Disorder | Patients (of 244 surgical) | Prevalence |
|---|---|---|
| Depression | 65 | 26.6% |
| Anxiety | 65 | 26.6% |
| Substance use | 65 | 26.6% |

Three identical counts. The natural reviewer reaction — "the chance of that is
astronomically small, so it must be a coding error" — is the right instinct to
have. The rest of this note is the audit that instinct demands.

---

## 2. The key fact: equal totals, *different patients*

The three groups of 65 are **not the same 65 people**. Cross-tabulating the
three disorders at the patient level gives a fully disjoint partition of the 244
patients:

| depression | anxiety | substance use | n |
|:---:|:---:|:---:|---:|
| ● | ● | ● | 13 |
| ● | ● | ○ | 25 |
| ● | ○ | ● | 7 |
| ● | ○ | ○ | 20 |
| ○ | ● | ● | 9 |
| ○ | ● | ○ | 18 |
| ○ | ○ | ● | 36 |
| ○ | ○ | ○ | 116 |

(● = present, ○ = absent; the eight rows are mutually exclusive and sum to 244.)

The marginals of this table are what produce the three 65s:

- Depression = 13 + 25 + 7 + 20 = **65**
- Anxiety = 13 + 25 + 9 + 18 = **65**
- Substance use = 13 + 7 + 9 + 36 = **65**

But the *membership* differs sharply: 20 patients have depression alone, 18
anxiety alone, 36 substance use alone, and only 13 have all three. A copy/paste
or column-duplication bug would make the three groups **identical** (every
overlap cell would be 65 or 0). Here the overlap structure is rich and
asymmetric. **Equal totals + different members = coincidence, not duplication.**

---

## 3. How unlikely is the coincidence, really?

A reviewer estimated the probability of the three matching at roughly
3 × 10⁻²². That figure answers the wrong question. It corresponds to demanding
three *pre-specified, independent* events to each land on one *pre-specified*
exact value with no shared sampling support. The data pose a much milder
question: given three binomial counts out of 244 with similar underlying rates,
how often do they coincide on the same integer?

Computing this directly (`scipy.stats.binom`, n = 244):

| Quantity | Probability |
|---|---|
| Two independent counts equal (common p = 0.266) | ~0.041 (1 in 24) |
| **All three counts equal each other (common p = 0.266)** | **~0.0019 (1 in ~519)** |
| All three equal, heterogeneous rates (0.319 / 0.282 / 0.266) | ~0.0008 |
| All three land on exactly 65 (common p) | ~1.9 × 10⁻⁴ |

So the equality is a **~0.2% small-sample event — uncommon but utterly ordinary**,
and roughly **nineteen orders of magnitude more likely** than the 3 × 10⁻²²
estimate. Crucially, the probability argument is secondary: section 2 already
settles it, because the raw records show the three groups are different people.

> Intuition: a binomial count out of 244 at p ≈ 0.27 has a standard deviation of
> only ~6.9. Three such counts cluster tightly around 65, so a tie is a
> coin-flip-scale curiosity, not a miracle.

---

## 4. Independent verification (two code paths, matching provenance)

The result was re-derived from the **raw** MIMIC-IV `hosp/diagnoses_icd.csv.gz`
by two independent implementations that share no code:

1. **pandas streaming** (`src/mimic/...`) — chunked read, `str.startswith`
   prefix matching, patient-level aggregation.
2. **DuckDB / SQL** (`src/mimic/verify_triple65_duckdb.py`) — version-aware
   `LIKE` prefix matching, `GROUP BY subject_id`.

Both yield **65 / 65 / 65**, the **identical** disjoint table above, and
**0 disagreements** when the re-derived per-patient flags are compared against
the stored cohort flags (244 patients × 3 disorders = 732 checks, all matching).
Input fingerprints (MD5) are recorded so anyone can confirm they used the same
files:

```
diagnoses_icd.csv.gz : 53535040f59bd4f2a68de9c9c04876f1
cohort CSV           : 6fec977f756603fc3f380b560e367a34
```

---

## 5. Why the rates land near each other in the first place

This is a **referral-filtered surgical population**, not the general public.
Patients reach epilepsy surgery after years of drug-resistant epilepsy, during
which depression, anxiety, and substance-use disorders accrue at broadly similar
clinical rates (each roughly a quarter to a third of patients in this and prior
cohorts). When three true rates sit close together, their sample counts out of a
few hundred patients frequently land within a point or two — and occasionally
exactly tie. The tie is a feature of small integers and similar rates, not of
the pipeline.

---

## 6. Reproduce it yourself

You need credentialed access to **MIMIC-IV v3.1** from PhysioNet (we cannot
redistribute the patient-level data). Then:

```bash
export MIMIC_ROOT=/path/to/physionet.org/files/mimiciv/3.1
pip install -r requirements.txt
python src/mimic/verify_triple65_duckdb.py     # prints 65/65/65, disjoint table, MD5s
python src/mimic/coincidence_math.py           # prints the probabilities in section 3
pytest tests/                                  # invariant checks
```

The ICD prefix definitions used for every disorder are in
`src/common/icd_codes.py` and are quoted in the manuscript supplement.

---

### Bottom line

Three equal prevalences looked implausible, so we audited it the way a skeptical
reviewer would: we re-derived it twice from the raw records, confirmed the three
groups are different patients, checked every per-patient flag, fingerprinted the
inputs, and computed the *correct* coincidence probability. The 26.6% × 3 result
survives all of it. It is a real, reproducible small-sample coincidence — and the
raw evidence is available to credentialed reviewers on request.
