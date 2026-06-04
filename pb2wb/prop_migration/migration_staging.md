# P721 → P129 Migration Staging Plan

Pre-selected test cases for the live rollout of `apply_basis_migration.py`.
These were chosen deliberately before touching production data; don't substitute
them ad hoc.

Every stage should be verified before advancing.

---

## Stage 1 — Dry run (no FactGrid changes)

**Status: DONE**

```bash
python prop_migration/apply_basis_migration.py --basis "Faulhaber" --dry-run
```

Result: 8,347 items found via SPARQL; candidate resolved to P129=Q164508.
Shallow dry-run (WBManager not needed without credentials).

---

## Stage 2 — Single-item live test

**Status: DONE** (2026-06-02)

**Basis:** `Perea 2004`  
**Target item:** Q1086665  
**Item label:** Juan Tallante, regidor de Murcia, *Obra en loor de veinte excelencias de Nuestra Señora*, escrito 1488 ca.  
**Statements to convert on this item:** 1  
**Total items with P721="Perea 2004" in FactGrid:** 8  
**ref_qid (P129):** Q1071227 — Perea Rodríguez (2004), "Las cortes literarias hispánicas del siglo XV..."  
**match_type in TSV:** vetted (Charles approved), no locator

**Why this item:** Q1086665 has only 1 P721="Perea 2004" statement and 2 total
P721 statements, making the before/after trivially verifiable on the FactGrid UI.

```bash
python prop_migration/apply_basis_migration.py --basis "Perea 2004" --item Q1086665
```

**Verification:** Open https://database.factgrid.de/wiki/Q1086665 and confirm:
- P129 = Q1071227 appears in the references section of the affected statement
- pq:P721 = "Perea 2004" is gone from that statement's qualifier section
- All other statements on the item are unchanged

---

## Stage 3 — Low-frequency full run

**Status: PENDING** (run after Stage 2 is verified)

**Basis:** `Cuartero`  
**ref_qid (P129):** Q1068432 — Cuartero y Huerta et al. (1949-79), *Índice...*  
**match_type in TSV:** vetted (Charles approved), no locator  
**Frequency in TSV:** 10  
**Items in FactGrid with P721="Cuartero":** 7  

**Why this basis:** Freq=10 / 7 items keeps blast radius small for first multi-item
run. `match_type=vetted` means Charles explicitly approved Q1068432. No locator
means the reference snak is a simple P129=item with nothing else to go wrong.

```bash
python prop_migration/apply_basis_migration.py --basis "Cuartero"
```

**Verification:** Spot-check runs automatically after the script completes.
Manually inspect 1-2 items from the SPARQL list if the spot-check reports any
failures.

---

## Stage 4 — Perea 2004 full run

**Status: PENDING** (run after Stage 3 is verified)

**Basis:** `Perea 2004`  
**ref_qid (P129):** Q1071227  
**Items in FactGrid:** 8 (Stage 2 item Q1086665 will be skipped via progress log)

```bash
python prop_migration/apply_basis_migration.py --basis "Perea 2004"
```

---

## Stage 5 — High-frequency batch (top 35 bases, 50% coverage)

**Status: PENDING** (run after Stage 4 verified)

**Coverage target:** 50% of actionable usages (64,600 / 128,927)  
**Bases to run:** 35 distinct `--basis` values (all with freq ≥ 332)  
**Execution:** batch runner (see below)

Top of the list (sorted by descending frequency):

| # | Freq  | Basis            | ref_qid   |
|---|-------|------------------|-----------|
| 1 | 21531 | Faulhaber        | Q164508   |
| 2 | 6488  | Zarco            | Q1345183  |
| 3 | 5708  | IGM              | Q395978   |
| 4 | 3746  | BNE Cat.         | Q396047   |
| 5 | 3374  | Wikidata         | Q370382   |
| 6 | 3323  | DB~e             | Q550714   |
| 7 | 3168  | Wikipedia        | Q629842   |
| 8 | 2690  | Norton           | Q1068254  |
| … | …     | (see TSV, vetted=Y, freq ≥ 332) | |

> **Note:** Faulhaber alone has 8,347 items. At 2s/item + write overhead,
> each large basis takes hours. Use `--max-statements 500` to run in chunks
> across sessions; the progress log makes each restart seamless.

---

## Coverage thresholds (computed 2026-05-31 from P721-P129.tsv)

All figures are actionable usages (excluded rows removed). Total = 128,927.

| Coverage | Bases to run | Min freq | Usages covered |
|----------|-------------|----------|----------------|
| 50%      | 35          | ≥ 332    | 64,600         |
| 60%      | 119         | ≥ 80     | 77,394         |
| 70%      | 433         | ≥ 19     | 90,250         |
| 75%      | 2,513       | ≥ 1      | 96,696         |
| 80%      | not reachable with current vetted=Y set | — | — |

**Key implication:** 70% is achievable by running 433 bases (a day or two of
compute). Getting the final 5% to 75% requires running all 2,513 vetted=Y
bases — including 2,080 low-frequency ones (freq 1–18). This is only feasible
with the batch runner script; don't attempt it interactively.

The 75% target corresponds to Charles having vetted 96,696 of 128,927
actionable statement usages. Rows not yet vetted by Charles (vetted blank)
are excluded from all runs.

---

## Batch execution (Stages 5+)

Running 433+ `--basis` commands manually is not feasible. The execution model is:

```bash
# 1. Generate the run list from the TSV (frequency-descending, vetted=Y only)
python prop_migration/run_basis_batch.py --min-freq 332 --dry-run   # preview
python prop_migration/run_basis_batch.py --min-freq 332             # execute

# 2. After confirming Stage 5, lower the threshold
python prop_migration/run_basis_batch.py --min-freq 80
python prop_migration/run_basis_batch.py --min-freq 19
python prop_migration/run_basis_batch.py --min-freq 1   # final 75% push
```

`run_basis_batch.py` does not exist yet. It needs to:
- Read `P721-P129.tsv`, filter `vetted=Y` + valid QID, sort by descending freq
- Skip any basis already fully converted (check progress log vs SPARQL count)
- Call `apply_basis_migration.py` for each remaining basis, passing `--delay`
- Log a summary line after each basis completes (basis, items, statements, errors)
- Support `--min-freq`, `--max-freq`, and `--limit N` (run only first N bases)
- Support `--dry-run` (shows what would be run without writing)

Build `run_basis_batch.py` before starting Stage 5.

---

## Progress log

The script appends a JSONL record to `prop_migration/basis_migration_progress.jsonl`
for every successfully converted statement GUID. Each run is fully resumable:
re-running the same `--basis` command skips already-converted GUIDs automatically.

To see overall progress at any time:

```bash
python - <<'EOF'
import json, csv

done = set()
with open('prop_migration/basis_migration_progress.jsonl') as f:
    for line in f:
        try: done.add(json.loads(line)['basis'])
        except: pass
print(f'{len(done)} distinct basis values fully converted so far')
EOF
```
