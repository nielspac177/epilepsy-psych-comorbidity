# The code explained for dummies

This is a teaching walkthrough of the analysis code in this repository. It
assumes you have never written a line of Python. The goal is that by the end you
can open any script here, read it, and understand what each line does and why it
is there.

We do not teach Python in the abstract and then apply it. We read the real code,
line by line, and learn each piece of the language at the moment it first shows
up. The code happens to be a medical study (psychiatric diagnoses in epilepsy
surgery patients), but you do not need any medical or statistics background to
follow along. If you are a reviewer who just wants to confirm the analysis is
sound, you can read this top to bottom and check the logic yourself.

A note on how to read the code blocks: lines that start with `#` are comments.
The computer ignores them. They are notes from the author to whoever reads the
code next, which now includes you.

---

## Chapter 0. What Python is, and how to run it

Python is a language for giving a computer instructions. You write those
instructions in a plain text file ending in `.py`, and then you run that file.
The computer reads it from top to bottom and does what each line says.

To follow along you need Python installed. On most Macs and Linux machines it is
already there. Open a terminal and type:

```bash
python3 --version
```

If you see something like `Python 3.12.0`, you are ready. To run one of the files
in this project, you type `python3` followed by the path to the file:

```bash
python3 src/mimic/verify_triple65_duckdb.py
```

That is the whole model. You write instructions in a file, you run the file, the
computer does the work and usually prints something back to you.

---

## Chapter 1. The smallest real file: storing facts

Open `src/common/icd_codes.py`. This file does not calculate anything. Its only
job is to write down a set of facts that the rest of the project relies on: which
diagnostic codes count as epilepsy, and which count as each psychiatric disorder.

A "diagnostic code" here is an ICD code. Hospitals record every diagnosis as a
short code from a standard list. `G40` means epilepsy. `F32` means a depressive
episode. We will use those codes constantly, so we store them in one place.

The file opens with a triple-quoted block:

```python
"""
ICD-9 and ICD-10 code definitions for epilepsy and psychiatric comorbidity study.
These are used as prefix matches (e.g., 'G40' matches G40.001, G40.101, etc.)
"""
```

Three double-quotes start a string that can run across many lines, and three more
end it. When a string like this sits at the very top of a file on its own, Python
treats it as documentation. It does nothing when the program runs. It is there to
tell a human what the file is for.

### Variables

Next comes our first real instruction:

```python
EPILEPSY_ICD10 = {
    "G40": "Epilepsy and recurrent seizures (all subtypes)",
}
```

Read the `=` as "is set to." We are creating a **variable** named
`EPILEPSY_ICD10` and putting something into it. A variable is just a name that
points at a value, so we can refer to that value later by its name instead of
writing it out again.

The all-capitals name is a convention. Python does not require it, but
programmers write names in capitals to signal "this is a fixed fact that should
not change while the program runs." A reader sees `EPILEPSY_ICD10` and knows it
is a settled definition.

### Strings

The pieces in quotes, like `"G40"` and `"Epilepsy and recurrent seizures"`, are
**strings**. A string is text. Anything inside quotes is treated as literal
characters, not as an instruction. `"G40"` is the three characters G, 4, 0.

### Dictionaries

The curly braces `{ }` make a **dictionary**. A dictionary stores pairs. On the
left of each colon is a "key," on the right is a "value." Here the key is the code
`"G40"` and the value is its English description. You can think of a dictionary as
a small lookup table: give it a key, it hands you back the matching value.

We only strictly need the code `"G40"` for the analysis. The description is there
so a human reading the file understands what the code means. Storing both keeps
the meaning next to the code it describes.

### Lists, and nesting

Now look at the heart of the file:

```python
PSYCH_CATEGORIES = {
    "depression": {
        "label": "Depressive Disorders",
        "icd10": ["F32", "F33", "F341"],
        "icd9":  ["2962", "2963", "3004", "311"],
    },
    ...
}
```

This is a dictionary inside a dictionary. The outer dictionary has one entry per
disorder. The key is `"depression"`. The value is itself another dictionary
describing that disorder.

Inside, `"icd10"` points at `["F32", "F33", "F341"]`. The square brackets `[ ]`
make a **list**. A list is an ordered collection of items. This one holds three
strings. So we are saying: depression, in the ICD-10 coding system, is any of the
codes that start with F32, F33, or F341.

Two design choices in this list carry real weight later.

First, we wrote `"F341"` and not `"F34"`. The code `F341` is dysthymia, a form of
depression. The shorter `F34` would also catch `F340`, which is cyclothymia, a
bipolar condition. By writing the longer, more specific prefix, we make sure the
depression group does not accidentally pull in a bipolar diagnosis.

Second, depression, anxiety, and substance use are given separate, non-overlapping
code lists. No code appears in two disorders. That is what makes it impossible for
a single diagnosis to be counted twice, and it is a fact the tests in this project
actively check.

There are two lists per disorder, `"icd10"` and `"icd9"`, because hospitals
switched coding systems partway through the study period. The same disorder has
different codes in the old system (ICD-9) and the new one (ICD-10), so we keep
both and use whichever matches a given record.

That is the entire file: named facts, stored as nested dictionaries and lists. No
calculation yet. Every other script in the project imports these definitions
instead of writing its own, so there is exactly one place to look if you want to
know how a disorder was defined.

---

## Chapter 2. A function that makes a decision

Storing codes is useless until we can ask a question with them: does a given
diagnosis code belong to a given disorder? That question is answered by a small
**function**. You can see it in `tests/test_icd_matching.py`:

```python
def matches(code: str, version: int, disorder: str) -> bool:
    prefixes = PSY[disorder]["icd10"] if version == 10 else PSY[disorder]["icd9"]
    return any(str(code).startswith(p) for p in prefixes)
```

A function is a named, reusable piece of logic. You give it some inputs, it gives
you back an answer. Once it exists, you can use it as many times as you like
without rewriting it. This is the single most important idea in programming: name
a piece of work once, reuse it everywhere.

### Defining the function

```python
def matches(code: str, version: int, disorder: str) -> bool:
```

`def` means "define a function." `matches` is the name we are giving it. The names
inside the parentheses are the **parameters**: the inputs the function expects.
This function takes three: a `code` (like `"F329"`), a `version` (9 or 10), and a
`disorder` (like `"depression"`).

The little notes `: str`, `: int`, and `-> bool` are **type hints**. They are
optional labels that tell a reader what kind of value each input should be and
what the function gives back. `str` means a string (text), `int` means an integer
(a whole number), and `bool` means a boolean. We will meet booleans in a moment.
Python does not enforce these hints; they are documentation that tools can also
read.

The line ends in a colon, and the lines that belong to the function are indented
underneath it. Indentation is how Python groups lines together. Everything
indented under the `def` line is the body of the function.

### Choosing the right list

```python
prefixes = PSY[disorder]["icd10"] if version == 10 else PSY[disorder]["icd9"]
```

`PSY` is the dictionary of disorders we built in Chapter 1 (imported under a short
name). `PSY[disorder]` looks up one disorder by its key. If `disorder` is
`"depression"`, then `PSY["depression"]` hands back depression's inner dictionary.
Adding `["icd10"]` then reaches into that and pulls out the ICD-10 list.

The rest of the line is a compact decision. Read it as a sentence: use the icd10
list **if** the version is 10, **else** use the icd9 list. The double equals `==`
asks a question: "is version equal to 10?" A single `=` would mean "set version to
10," which is not what we want here. One equals sets a value; two equals compares
two values. Mixing these up is one of the most common beginner mistakes.

Whichever list we pick gets stored in a new variable called `prefixes`.

### Booleans and the actual test

```python
return any(str(code).startswith(p) for p in prefixes)
```

`return` hands a value back to whoever called the function. That value is the
function's answer.

A **boolean** is a value that is either `True` or `False`. There are only those
two. They are how a program represents yes/no questions, and they are exactly what
we want here: does this code belong to this disorder, yes or no?

Now read the inside from the middle outward. `for p in prefixes` walks through the
list one item at a time, calling each item `p`. So `p` becomes `"F32"`, then
`"F33"`, then `"F341"`. For each one, `str(code).startswith(p)` asks: does the
code begin with this prefix? `str(code)` makes sure the code is treated as text,
and `.startswith(p)` is a built-in test that returns `True` if the text starts
with `p` and `False` otherwise. So `"F329".startswith("F32")` is `True`.

That produces a series of True/False answers, one per prefix. `any(...)` collapses
them into a single answer: it is `True` if **at least one** of them was true. In
plain words, the whole line says: the code matches this disorder if it starts with
any of the disorder's prefixes.

This is why we call it prefix matching. We never list every possible code. We list
the beginnings, and any code that starts that way counts. `F32` quietly covers
`F320`, `F321`, `F3289`, and the rest of the family, with one short entry.

This one function is the engine of the entire study. Every prevalence number in
the paper comes from asking this same question, millions of times, across every
diagnosis in the database.

---

## Chapter 3. Reading a table of data

So far we have hand-typed values. Real data lives in files with hundreds of
thousands of rows. To work with those, the project uses a tool called **pandas**.
Pandas is not part of Python itself; it is an add-on library that you install
once and then bring into a script when you need it.

### Importing a library

At the top of scripts that handle data you will see:

```python
import pandas as pd
```

`import pandas` loads the library. `as pd` gives it a shorter nickname so we can
type `pd` instead of `pandas` every time. This nickname is a near-universal
convention; almost every Python project in the world writes `pd`.

### What pandas gives you

Pandas reads a data file into a thing called a **DataFrame**. A DataFrame is a
table, the same idea as a spreadsheet: rows and named columns. You can see this in
`src/mimic/build_evidence.py`:

```python
cohort = pd.read_csv(COHORT_FILE)
```

`pd.read_csv(...)` reads a comma-separated file from disk and returns a DataFrame.
We store it in a variable called `cohort`. Now `cohort` holds the whole table of
patients in memory, and we can ask questions of it.

### Filtering rows

A few lines later:

```python
surg = cohort[cohort["surgical"] == 1].copy()
```

This keeps only the surgical patients. Read the inside first. `cohort["surgical"]`
selects one column, the one named `surgical`, which holds a 1 for surgical
patients and a 0 for everyone else. `cohort["surgical"] == 1` compares every value
in that column to 1 and produces a column of True/False answers, one per patient.

Then `cohort[ ... ]` uses that column of booleans to filter: it keeps only the
rows where the answer was True. So `surg` ends up holding just the surgical
patients. The `.copy()` at the end makes an independent copy, which avoids a
category of confusing bugs where changing the small table accidentally reaches
back and changes the big one.

The very next line is a safety check:

```python
assert len(surg) == 244, len(surg)
```

`len(surg)` counts the rows. `assert` says "this must be true; if it is not, stop
everything immediately." We are stating out loud that there must be exactly 244
surgical patients. If a future version of the data has a different number, the
script halts here with a clear error instead of quietly producing wrong results
further down. Assertions are how you pin your assumptions in place so they cannot
drift silently.

---

## Chapter 4. Counting without double-counting

The central task of the study is counting patients, and the trap is counting the
same patient twice. A patient can have many hospital admissions, and many
diagnoses per admission. We want to know how many distinct *patients* have a
disorder, not how many diagnosis lines mention it.

The tool for "distinct things" is a **set**. A set is like a list, but it
automatically throws away duplicates. If you add the same patient to a set twice,
it still contains that patient once. That property is exactly what we need.

In `build_evidence.py` the counting loop looks like this, simplified:

```python
for chunk in pd.read_csv(DX_FILE, dtype={"icd_code": str}, chunksize=500_000):
    chunk = chunk[chunk["subject_id"].isin(surg_ids)]
    for _, r in chunk.iterrows():
        for dx in ("depression", "anxiety", "substance_use"):
            if matches(code, ver, dx):
                evidence[sid][dx].append(f"ICD-{ver}:{code}")
```

There is a lot here, so we take it one layer at a time.

### Reading a huge file in pieces

```python
for chunk in pd.read_csv(DX_FILE, dtype={"icd_code": str}, chunksize=500_000):
```

The diagnoses file is too large to comfortably load all at once. `chunksize=500_000`
tells pandas to read it 500,000 rows at a time and hand us one chunk on each pass
of the loop. The underscores in `500_000` are just visual separators for the
digits; Python ignores them. They make large numbers readable. `dtype={"icd_code": str}`
tells pandas to treat the code column as text, so a code like `0410` keeps its
leading zero instead of turning into the number 410.

`for chunk in ...:` is a **loop**. It repeats the indented block once for each
chunk, with `chunk` holding the current piece of the table each time.

### Keeping only our patients

```python
chunk = chunk[chunk["subject_id"].isin(surg_ids)]
```

This is the same filtering idea from Chapter 3. `surg_ids` is the set of patient
IDs we care about. `.isin(surg_ids)` produces a True/False column marking which
rows belong to one of our patients, and we keep only those. Every chunk gets
trimmed down to the patients in our cohort before we do any more work.

### Walking row by row

```python
for _, r in chunk.iterrows():
```

`.iterrows()` goes through the table one row at a time. Each pass gives us the row
in `r`. The underscore is a real Python convention worth knowing: `iterrows`
actually hands back two things, a row number and the row itself, and we only want
the row. Naming the part we are ignoring `_` is the standard way to say "I am
deliberately not using this."

### Asking the question for each disorder

```python
for dx in ("depression", "anxiety", "substance_use"):
    if matches(code, ver, dx):
        evidence[sid][dx].append(f"ICD-{ver}:{code}")
```

For the current diagnosis row, we loop over the three disorders. `if matches(...)`
calls the exact function from Chapter 2. If this code belongs to this disorder, we
record it.

`f"ICD-{ver}:{code}"` is an **f-string**, a convenient way to build text with
values dropped into it. The `f` before the quotes turns on this feature, and
anything inside curly braces is replaced by its value. If `ver` is 10 and `code`
is `F329`, this produces the string `"ICD-10:F329"`. We keep the actual code, not
just a yes/no, so that later anyone can audit exactly which diagnosis triggered
each flag.

`evidence[sid][dx].append(...)` files that string away under this patient (`sid`)
and this disorder (`dx`). Because a patient is recorded once per disorder
regardless of how many matching rows they have, counting them at the end gives
distinct patients, not diagnosis lines. That distinction is the whole reason the
surgical counts come out the way they do.

---

## Chapter 5. The verification script, line by line

Now we can read a complete script end to end. Open
`src/mimic/verify_triple65_duckdb.py`. Its job is to recompute the headline result
of the study from the raw records, using a completely separate method, as an
independent check. Reading it will tie together everything so far and introduce a
few new pieces.

### The imports

```python
import hashlib
import json
import os
from pathlib import Path

import duckdb
```

Each `import` brings in a library. `hashlib` computes fingerprints of files.
`json` reads and writes a common data format. `os` lets us talk to the operating
system. `from pathlib import Path` is a slightly different form: it reaches into
the `pathlib` library and pulls out just one tool, `Path`, so we can use the name
`Path` directly. `duckdb` is a small database engine we will use to do the
counting in a query language called SQL.

The blank line between the first group and `duckdb` is a convention: the standard
libraries that ship with Python go on top, then a blank line, then the add-on
libraries you installed. It is a small courtesy to the next reader.

### Finding the data without hard-coding a path

```python
MIMIC_ROOT = Path(
    os.environ.get("MIMIC_ROOT", "/Volumes/Niels 2/MIMIC/physionet.org/files/mimiciv/3.1")
)
DX_FILE = MIMIC_ROOT / "hosp" / "diagnoses_icd.csv.gz"
```

`os.environ.get("MIMIC_ROOT", default)` reads an **environment variable**. An
environment variable is a setting that lives outside the script, in your terminal.
The idea is that the location of the data is different on every computer, so we do
not bake one path into the code. Instead the script asks: "is there a setting
called `MIMIC_ROOT`?" If yes, it uses that. If not, it falls back to the second
value, the default. This is what lets the same script run unchanged on your
machine and on ours.

`Path(...)` wraps the location in a `Path` object, which knows how to build file
paths safely. The slash in `MIMIC_ROOT / "hosp" / "diagnoses_icd.csv.gz"` is not
division here. For `Path` objects, `/` joins folders and files into a full path,
the same way you would write them with slashes by hand, but in a way that works on
any operating system.

### A function that builds a question

```python
def sql_flag(dx: str) -> str:
    v10 = " OR ".join(f"icd_code LIKE '{p}%'" for p in PSY[dx]["icd10"])
    v9  = " OR ".join(f"icd_code LIKE '{p}%'" for p in PSY[dx]["icd9"])
    return f"MAX(CASE WHEN (icd_version = 10 AND ({v10})) " \
           f"OR (icd_version = 9 AND ({v9})) THEN 1 ELSE 0 END)"
```

This function does not count anything itself. It writes out a piece of a database
query as text, which we will hand to the database engine in a moment.

`for p in PSY[dx]["icd10"]` walks the disorder's prefix list, the same list from
Chapter 1. For each prefix `p` it builds the fragment `icd_code LIKE 'F32%'`. In
SQL, the database query language, `LIKE 'F32%'` means "starts with F32," where the
`%` stands for "anything can follow." It is the SQL version of the `startswith`
test from Chapter 2.

`" OR ".join(...)` glues those fragments together with the word `OR` between them,
producing one long condition like `icd_code LIKE 'F32%' OR icd_code LIKE 'F33%' OR
icd_code LIKE 'F341%'`. The `OR` means any of them counts, which mirrors the
`any(...)` we used before.

The backslash `\` at the end of the line is a line-continuation. It tells Python
the statement keeps going on the next line, so a long string can be split across
two lines for readability without changing its meaning.

The returned text is a SQL `CASE` expression that reads, in English: if the
diagnosis is an ICD-10 record and matches the version-10 list, or it is an ICD-9
record and matches the version-9 list, count it as 1, otherwise 0. Wrapping it in
`MAX(...)` later turns "did any of this patient's records match" into a single 1
or 0 per patient. This is the patient-level distinct-counting idea from Chapter 4,
expressed in SQL instead of Python loops. Same logic, different engine, which is
exactly the point of an independent check.

### Guarding the assumptions

```python
n_surg = con.execute("SELECT count(*) FROM cohort WHERE surgical = 1").fetchone()[0]
assert n_surg == 244, f"expected 244 surgical, got {n_surg}"
```

We run a query that counts surgical patients and read the single number back. Then
we assert it equals 244, the same kind of guard rail we met in Chapter 3. If the
cohort ever changes shape, the script stops here and says so plainly.

### Catching a patient who would otherwise vanish

```python
INSERT INTO derived
SELECT c.subject_id, 0, 0, 0 FROM cohort c
WHERE c.surgical = 1 AND c.subject_id NOT IN (SELECT subject_id FROM derived)
```

This handles a subtle case. The main query only sees patients who appear in the
diagnoses file. A surgical patient with zero diagnosis records would simply be
missing, which would quietly shrink the denominator below 244. This statement adds
any such patient back in with all-zero flags, so every one of the 244 patients is
accounted for. This exact failure mode is one of the things the project's
adversarial checks were written to catch, and handling it here is why they find
nothing.

### Checking the new answer against the stored one

```python
disagree = con.execute("""
    SELECT count(*) FROM derived d
    JOIN cohort c ON c.subject_id = d.subject_id
    WHERE d.dep <> c.has_depression
       OR d.anx <> c.has_anxiety
       OR d.sub <> c.has_substance_use
""").fetchone()[0]
```

The script does not trust its own recomputation on its own. This query lines up
each patient's freshly computed flags against the flags already stored in the
cohort file and counts how many disagree. `<>` means "not equal to" in SQL. The
expected answer is zero. If the new method and the stored data ever disagreed
about even one patient, this number would be greater than zero and we would know
immediately. It comes out zero, which is the strongest single sign that the result
is solid: two independent paths reach the same answer for all 244 patients.

The script ends by writing its results out and returning an exit code that is
"success" only if the counts came out right and nothing disagreed. That way the
script can be run automatically and will loudly fail if anything ever drifts.

---

## Chapter 6. Cleaning data that fights back

Real data is messy, and a good chunk of real analysis code exists only to clean it
up. `src/mgb/parse_phq_gad.py` is a clear example. The hospital exported some
follow-up questionnaire scores as plain numbers, but others as text wrapped in
brackets like `"[13]"`, and one as `"0 (Phq4score)"`. A naive read would silently
drop every messy value and quietly undercount. This function fixes that:

```python
def parse_score(x) -> float:
    if pd.isna(x):
        return np.nan
    s = str(x).strip().replace("[", "").replace("]", "")
    m = re.search(r"-?\d+\.?\d*", s)
    return float(m.group()) if m else np.nan
```

### Handling missing values

```python
if pd.isna(x):
    return np.nan
```

In data work, many cells are simply empty. Pandas represents an empty cell as a
special value called `NaN`, which stands for "not a number." `pd.isna(x)` asks "is
this value missing?" If it is, we return `np.nan`, the same kind of missing marker,
and stop. There is nothing to parse, so we say so honestly rather than guessing.

### Stripping the junk

```python
s = str(x).strip().replace("[", "").replace("]", "")
```

This line chains several text operations left to right. `str(x)` makes sure we are
working with text. `.strip()` removes spaces from the ends. `.replace("[", "")`
deletes any left bracket by replacing it with nothing, and `.replace("]", "")` does
the same for the right bracket. So `"[13]"` becomes `"13"`. Each operation hands
its result to the next, which is why they can be written in a row like this.

### Finding the number with a pattern

```python
m = re.search(r"-?\d+\.?\d*", s)
```

`re` is Python's tool for **regular expressions**, which are patterns for finding
text. The pattern `r"-?\d+\.?\d*"` describes "a number." Reading its parts: `-?`
means an optional minus sign, `\d+` means one or more digits, `\.?` means an
optional decimal point, and `\d*` means any number of digits after it. The `r`
before the quotes marks it as a raw string, which keeps the backslashes literal so
the pattern reads as written.

`re.search` looks through the text for the first stretch that matches the pattern
and hands back a small result object, or nothing if it found no number.

### Returning a clean number, or admitting defeat

```python
return float(m.group()) if m else np.nan
```

If `re.search` found something, `m` holds it and `m.group()` pulls out the matched
text, which we convert to an actual number with `float(...)`. A `float` is a number
that can have a decimal point. If `re.search` found nothing, `m` is empty, the
`else` branch runs, and we return the missing marker. So a cell like `"declined"`,
which holds no number, comes back as missing instead of crashing the program or
turning into a wrong value.

Four lines of careful handling, and they are the difference between using all of
the data and silently using two-thirds of it. This is what a lot of honest
analysis code actually looks like: not clever, just careful about the cases real
data throws at you.

---

## Chapter 7. The MGB symptom analysis: coalescing messy timepoints

Chapter 6 recovered the individual PHQ-9 and GAD-7 scores. This chapter turns
them into the answers two reviewer questions asked for: how many patients
improved by a clinically meaningful amount, and whether the patients who have
scores differ from those who do not. The code lives in
`src/mgb/build_mgb_analysis_dataset.py` and `src/mgb/recompute_b11_b13_final.py`.

### Coalescing two columns into one baseline

The source workbook stores each instrument across three columns: two early
measurements and one final follow-up. We want a single baseline value per patient
and a single follow-up value. In the dataset builder:

```python
phq["phq9_pre"] = phq["phq9_baseline"].fillna(phq["phq9_mid"])
phq["phq9_post"] = phq["phq9_followup"]
```

`fillna` is the key idea. `phq["phq9_baseline"]` is the earliest column, but it is
sparsely filled. `.fillna(phq["phq9_mid"])` says: keep the baseline value where it
exists, and wherever it is missing, fill in from the second column instead. The
result, `phq9_pre`, is a single baseline that uses the earliest available score
for each patient. This is called a coalesce, and it matters because it nearly
quadruples how many patients have a usable baseline, which is what lets the paired
analysis run on 47 patients instead of 11. The follow-up, `phq9_post`, is just the
last column. The same two lines repeat for the GAD-7.

### Counting who improved

The improvement calculation is one small function in the recompute script. The
heart of it:

```python
a, b = num(d[pre]), num(d[post])
m = a.notna() & b.notna()
drop = a[m] - b[m]
n = int(m.sum())
```

`a` and `b` are the before and after columns. `m = a.notna() & b.notna()` builds a
boolean mask that is true only for patients who have **both** a before and an
after score; the `&` combines the two conditions element by element. `a[m] - b[m]`
then subtracts after from before for just those patients, so a positive `drop`
means the score went down, which for these scales means the patient improved.
`int(m.sum())` counts the paired patients, because adding up a column of True/False
treats each True as 1.

```python
ed, fx = ED50[label], FIXED[label]
"n_ed50": int((drop >= ed).sum()),
"pct_ed50": round(100 * (drop >= ed).mean(), 1),
```

`ED50` and `FIXED` are dictionaries holding the two thresholds for "clinically
meaningful" (3.7 and 5 points for the PHQ-9, for example). `drop >= ed` compares
every patient's drop to the threshold and produces another column of True/False.
Summing it counts how many cleared the bar; taking its `.mean()` gives the
fraction who did, which times 100 is the percentage. So two short expressions turn
a column of score changes into "12 of 47 patients improved, which is 25.5%."

```python
from scipy.stats import wilcoxon
p = float(wilcoxon(a[m], b[m]).pvalue) if n > 0 and (a[m] != b[m]).any() else float("nan")
```

`wilcoxon` is a ready-made statistical test from the SciPy library. It compares the
before and after scores as matched pairs and returns, among other things, a
`pvalue` telling you how likely the observed change is under no real effect. The
`if ...` guard avoids calling it when there is nothing to test (no pairs, or every
pair identical), returning the missing marker instead of crashing.

### The trajectory test, and the figures

The before-and-after change in a yes/no outcome (does the patient have a
psychiatric diagnosis) uses a different test, McNemar's test, from `statsmodels`,
which is built for paired yes/no data. The plotting script,
`src/mgb/make_b11_b13_figures.py`, then draws the paired slope plots and trajectory
lines with `matplotlib`. Those are worth reading once you are comfortable with the
chapters above; they use the same column names and the same masks, just to draw
instead of to count.

The lesson of this chapter is that most of real analysis is not exotic. It is
careful column handling (`fillna`), boolean masks, and a couple of well-chosen
library calls. The judgment is in deciding *which* columns mean what, which is why
those choices are written down explicitly in the code and the documentation rather
than buried.

---

## Chapter 8. The statistical layer, and where to go from here

The remaining scripts build on everything above and lean on standard statistical
libraries. You do not need to read them line by line to trust the pipeline, but
here is what each one is for, so you know where to look:

- `src/mimic/03_psm_analysis.py` matches each surgical patient to a similar
  non-surgical patient, so the two groups can be compared fairly. The technique is
  called propensity-score matching.
- `src/mimic/06_balance_prepost.py` produces the table that shows the matched
  groups really are similar on the things we matched on.
- `src/mimic/09_logreg_full.py` runs the main regression model that estimates how
  surgery relates to psychiatric diagnoses after accounting for other factors.
- `src/nis/import_nis.py` and `NIS_Analysis.ipynb` load the national survey data
  and run the trend models that account for the survey's sampling design.

Every one of these imports its disorder definitions from
`src/common/icd_codes.py`. None of them redefines a code list. That single rule,
one source of truth for the definitions, is what lets the three datasets be
compared on equal footing and what lets a reviewer audit the whole study by
reading one short file.

If you want to keep learning Python from here, the most useful next steps are the
official Python tutorial for the language itself, and the pandas "10 minutes to
pandas" guide for the data tools. But you now have something more useful than a
tutorial: a real codebase you can read. Open any `.py` file in this project and
you will recognize the pieces. That recognition is the whole skill.
