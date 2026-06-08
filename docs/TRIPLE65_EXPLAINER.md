# Why three psychiatric diagnoses share the same prevalence in MIMIC-IV, and why that is correct

In the MIMIC-IV surgical epilepsy cohort, depression, anxiety, and substance-use
disorder each show up in exactly 65 of 244 patients (26.6%). Three different
disorders, three identical counts. That looks wrong, and a careful reader should
stop on it. This note walks through what is actually going on, using aggregate
counts only (no patient-level data, in keeping with the PhysioNet MIMIC data use
agreement).

The short version: the three groups of 65 are different people. The number 65
repeats; the patients behind it do not.

## The thing that makes it look like a bug

If you saw three columns in a spreadsheet all reading 65, your first guess would
be a copy/paste error or a duplicated column. That guess is reasonable, so we
checked it directly instead of waving it away.

## The patient-level breakdown

The three disorders overlap, but not evenly. Here is the full cross-tabulation of
the 244 patients. Every patient falls into exactly one row.

| depression | anxiety | substance use | n |
|:---:|:---:|:---:|---:|
| yes | yes | yes | 13 |
| yes | yes | no  | 25 |
| yes | no  | yes | 7  |
| yes | no  | no  | 20 |
| no  | yes | yes | 9  |
| no  | yes | no  | 18 |
| no  | no  | yes | 36 |
| no  | no  | no  | 116 |

Add up the rows where depression is "yes": 13 + 25 + 7 + 20 = 65. Do the same for
anxiety: 13 + 25 + 9 + 18 = 65. And substance use: 13 + 7 + 9 + 36 = 65.

So the totals match, but look at who is in each group. Twenty patients have
depression and nothing else. Eighteen have anxiety alone. Thirty-six have a
substance-use disorder alone. Only 13 carry all three. If the 65s were a
duplicated column, every overlap cell would be 65 or 0. This table is nothing
like that. The groups are built from different patients who happen to total the
same number.

## We re-derived it four times, from the raw records

A matching table is only as trustworthy as the code that built it, so we rebuilt
the counts straight from the raw `hosp/diagnoses_icd.csv.gz` four separate ways.
Each implementation was written independently and shares no code with the others.

| Method | Result | Cross-check |
|---|---|---|
| DuckDB / SQL | 65 / 65 / 65 | 0 disagreements vs the stored flags |
| Streaming pandas | 65 / 65 / 65 | overlap table identical to the one above |
| Shell and awk (no pandas) | 65 / 65 / 65 | counts confirmed line by line |
| The cohort's own stored flags | 65 / 65 / 65 | matches the three derivations |

All four agree. When the re-derived per-patient flags are compared against the
flags stored in the cohort file, there are zero mismatches across all 244
patients and all three disorders. We also recorded MD5 fingerprints of the input
files so anyone can confirm they are working from the same data:

```
diagnoses_icd.csv.gz : 53535040f59bd4f2a68de9c9c04876f1
cohort CSV           : 6fec977f756603fc3f380b560e367a34
```

## We tried to break it, on purpose

Re-deriving the same number four ways still leaves the question: could all four
be making the same mistake? So we ran four deliberate attempts to prove the
result was an artifact. Each one failed.

- **Prefix over-reach.** Could a depression code be accidentally catching a
  bipolar code, inflating the count? No. The code lists for the three disorders
  share no prefixes, so no diagnosis can land in two groups. Removing the
  ICD-9 code `311` drops depression to 41, which confirms the contributing codes
  are real and specific rather than padding.
- **ICD-9 versus ICD-10 confusion.** Could version-9 and version-10 codes be
  matched against the wrong list? No. Swapping the two code lists collapses the
  counts to 0/0/0, which shows the versions are kept cleanly separate.
- **Admission versus patient counting.** Could the 65s come from failing to
  collapse multiple hospital admissions per patient? No. Counting at the
  admission level gives 220, 149, and 131, which is clearly asymmetric. The
  65/65/65 is specifically the correct one-row-per-patient result.
- **Cohort join error.** Could the join between the cohort and the diagnoses be
  dropping or duplicating patients? No. All 244 surgical patients are accounted
  for, none missing and none doubled.

## Why the rates sit close together to begin with

This is a referral-filtered surgical population, not the general public. Patients
reach epilepsy surgery after years of drug-resistant epilepsy, and over that time
depression, anxiety, and substance-use disorders accumulate at broadly similar
clinical rates, each landing somewhere around a quarter to a third of patients in
this cohort and in prior work. When three underlying rates are that close, three
counts out of a few hundred patients will often land within a point or two of
each other, and once in a while they tie exactly. The tie is arithmetic. It is
not the pipeline.

## Reproduce it yourself

You need credentialed access to MIMIC-IV v3.1 from PhysioNet; we cannot
redistribute the patient-level data. Then:

```bash
export MIMIC_ROOT=/path/to/physionet.org/files/mimiciv/3.1
pip install -r requirements.txt
python src/mimic/verify_triple65_duckdb.py     # prints 65/65/65, the overlap table, and the MD5s
pytest tests/                                  # checks the invariants
```

The ICD prefix lists for every disorder live in `src/common/icd_codes.py` and are
quoted in the manuscript supplement.

## Bottom line

Three equal prevalences looked implausible, so we audited it the way a skeptical
reviewer would. We re-derived it four times from the raw records, showed the
three groups are different patients, checked every per-patient flag, and
fingerprinted the inputs. The result holds. The raw evidence is available to
credentialed reviewers on request.
