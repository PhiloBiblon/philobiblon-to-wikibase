# P721 → P129 Migration Staging Plan

Pre-selected test cases for the live rollout of `apply_basis_migration.py`.
These were chosen deliberately before touching production data; don't substitute
them ad hoc.

Olaf will be watching. Every stage should be verified before advancing.

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

**Status: PENDING** (requires FactGrid credentials in settings.py)

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

## Stage 5+ — Scale up

After Stages 2-4 pass, advance to higher-frequency values. Suggested order
(all vetted=Y in TSV as of 2026-05-31):

| Freq  | Basis        | ref_qid   | match_type |
|-------|--------------|-----------|------------|
| 21531 | Faulhaber    | Q164508   | vetted     |
| 942   | Perea 2004   | Q1071227  | vetted     |
| ...   | (see P721-P129.tsv, filter vetted=Y) | | |

Use `--max-statements N` to cap each run during the ramp-up phase.

---

## Progress log

The script appends a JSONL record to `prop_migration/basis_migration_progress.jsonl`
for every successfully converted statement GUID. Each run is fully resumable:
re-running the same `--basis` command skips already-converted GUIDs automatically.
