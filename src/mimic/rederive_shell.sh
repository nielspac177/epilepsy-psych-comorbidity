#!/usr/bin/env bash
# Independent re-derivation of the MIMIC "Triple65" using shell tools only.
# Counts surgical patients flagged for depression / anxiety / substance_use
# via version-aware ICD prefix matching on diagnoses_icd.csv.gz.
set -euo pipefail

DX="/Volumes/Niels 2/MIMIC/physionet.org/files/mimiciv/3.1/hosp/diagnoses_icd.csv.gz"
COHORT="/Volumes/Niels 2/MIMIC/physionet.org/files/mimiciv/3.1/analysis/epilepsy_psych/epilepsy_patient_cohort_psm.csv"
OUT="/Users/nielspacheco/Desktop/Research/Rolston lab/Psych_epilepsy_surgery/repro_build/epilepsy-psych-comorbidity/verification_out"
mkdir -p "$OUT"

# 1) Surgical subject_id list (cohort col1=subject_id, col11=surgical).
#    Strip possible CR, require surgical==1. Sorted unique.
SURG="$OUT/surgical_ids.txt"
tr -d '\r' < "$COHORT" \
  | awk -F, 'NR>1 && $11==1 {print $1}' \
  | sort -u > "$SURG"
N_SURG=$(wc -l < "$SURG" | tr -d ' ')
echo "n_surgical = $N_SURG"

# 2) Scan diagnoses; for surgical subjects only, flag per-subject disorders
#    using version-aware prefix match. Emit one line per (subject,disorder)
#    deduped, then collapse to per-subject flags.
FLAGS="$OUT/subject_flags.txt"
gzcat "$DX" | tr -d '\r' | awk -F, -v surgfile="$SURG" '
BEGIN{
  while((getline s < surgfile) > 0){ surg[s]=1; ids[s]=1 }
  close(surgfile);
  # ICD10 prefixes
  split("F32 F33 F341", d10, " ");
  split("F40 F41", a10, " ");
  split("F10 F11 F12 F13 F14 F15 F16 F17 F18 F19", s10, " ");
  # ICD9 prefixes
  split("2962 2963 3004 311", d9, " ");
  split("30000 30001 30002 30021 30022 30023 30029", a9, " ");
  split("303 304 305", s9, " ");
}
function hasprefix(code, arr,   i){
  for(i in arr){ if(index(code, arr[i])==1) return 1 }
  return 0
}
NR>1 {
  sid=$1; code=$4; ver=$5;
  if(!(sid in surg)) next;
  if(ver==10){
    if(hasprefix(code,d10)) dep[sid]=1;
    if(hasprefix(code,a10)) anx[sid]=1;
    if(hasprefix(code,s10)) subF[sid]=1;
  } else if(ver==9){
    if(hasprefix(code,d9))  dep[sid]=1;
    if(hasprefix(code,a9))  anx[sid]=1;
    if(hasprefix(code,s9))  subF[sid]=1;
  }
}
END{
  # iterate over surgical ids so every subject appears (0/0/0 included)
  for(sid in ids){
    printf "%s\t%d\t%d\t%d\n", sid, (sid in dep)?1:0, (sid in anx)?1:0, (sid in subF)?1:0;
  }
}' > "$FLAGS"

# 3) Marginal counts
echo "depression    = $(awk -F'\t' '$2==1' "$FLAGS" | wc -l | tr -d ' ')"
echo "anxiety       = $(awk -F'\t' '$3==1' "$FLAGS" | wc -l | tr -d ' ')"
echo "substance_use = $(awk -F'\t' '$4==1' "$FLAGS" | wc -l | tr -d ' ')"

# 4) Disjoint overlap (dep,anx,sub,n)
echo "--- disjoint overlap (dep anx sub : n) ---"
awk -F'\t' '{print $2,$3,$4}' "$FLAGS" | sort | uniq -c \
  | awk '{printf "(%s,%s,%s) n=%s\n", $2,$3,$4,$1}'
