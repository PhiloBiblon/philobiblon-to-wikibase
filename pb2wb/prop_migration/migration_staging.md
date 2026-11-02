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

## Stage 2 — Single-item live tests

**Status: DONE** (2026-06-02 and 2026-06-04)

Two single-item pilots run:

**Perea 2004 / Q1086665** (2026-06-02): 1 statement converted. Verified on FactGrid UI.

**S. Leigh Sotheby & Co. / Q1080532** (2026-06-04): 1 statement converted. First run
with new `prop` and `main_value` fields in progress log (P34, "William Brownsword Chorley").

```bash
python prop_migration/apply_basis_migration.py --basis "Perea 2004" --item Q1086665
python prop_migration/apply_basis_migration.py --basis "S. Leigh Sotheby & Co." --item Q1080532
```

---

## Stage 3 — Low-frequency full run

**Status: DONE** (2026-06-02)

**Basis:** `Cuartero` — 10 statements, 7 items. 0 errors.

```bash
python prop_migration/apply_basis_migration.py --basis "Cuartero"
```

---

## Stage 4 — Perea 2004 full run

**Status: DONE** (2026-06-04)

**Basis:** `Perea 2004` — 7 remaining items (Q1086665 skipped via progress log).
7 converted, 0 errors, 7/7 spot-checks OK.

```bash
python prop_migration/apply_basis_migration.py --basis "Perea 2004"
```

---

## Stage 5 — Faulhaber (highest-frequency basis, run solo)

**Status: DONE** (2026-06-04 to 2026-06-05)

Faulhaber was run on its own before the batch runner, given its scale (8,347 items,
21,531 statements). Running it solo gave us reliable timing data and validated the
maintenance-window retry logic under real conditions.

**Results:** 21,252 converted, 0 errors, 20/20 spot-checks OK.  
**Elapsed:** ~17 hours (including daytime connection interruptions).  
**Measured rate:** 20.8 GUIDs/min avg (11/min daytime, 30/min overnight).  
**Timing model:** ~7.3s/item at `--delay 2`; estimated ~5.3s/item at `--delay 1`.

```bash
python prop_migration/apply_basis_migration.py --basis "Faulhaber"
```

Also completed in this phase: CCPBE (627 stmts, 412 items, ~44 min).

---

## Stage 6 — High-frequency batch (remaining top-35 bases)

**Status: IN PROGRESS** — Zarco next

**Use `--delay 1` from here on** (safe based on Faulhaber overnight performance; ~27% faster).

Top of the remaining list (sorted by descending frequency):

| # | Freq  | Basis      | Items  | ref_qid   | Status |
|---|-------|------------|--------|-----------|--------|
| 1 | 21531 | Faulhaber  | 8,347  | Q164508   | ✓ Done |
| 2 | 6488  | Zarco      | 2,095  | Q1345183  | **Next** (~3-4 hrs) |
| 3 | 5708  | IGM        | 15     | Q395978   | ⚠ Pilot first (380 GUIDs/item) |
| 4 | 3746  | BNE Cat.   | 1,689  | Q396047   | pending |
| 5 | 3374  | Wikidata   | —      | Q370382   | pending |
| 6 | 3323  | DB~e       | —      | Q550714   | pending |
| 7 | 3168  | Wikipedia  | —      | Q629842   | pending |
| 8 | 2690  | Norton     | —      | Q1068254  | pending |
| … | …     | (see TSV, vetted=Y, freq ≥ 332) | | | |

> **IGM warning:** Only 15 items but 5,708 GUIDs (~380/item). Each write is a
> massive payload. Do a single-item pilot before running the full 15.

```bash
# Run each basis individually with --delay 1
python prop_migration/apply_basis_migration.py --basis "Zarco" --delay 1

# Or use the batch runner for the remaining bases (skips already-done ones)
python prop_migration/run_basis_batch.py --min-freq 332 --delay 1
```

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

**Runtime estimate at `--delay 1`:** ~42 hours to complete all remaining vetted=Y bases
(~74,000 GUIDs remaining as of 2026-06-05). Spread across multiple sessions via the
batch runner; each restart resumes cleanly from the progress log.

**Key implication:** 70% is achievable by running 433 bases. Getting to 75% requires
running all 2,513 vetted=Y bases — only feasible with the batch runner.

---

## Batch execution

```bash
# Preview
python prop_migration/run_basis_batch.py --min-freq 332 --delay 1 --dry-run

# Run top-35 (50% coverage target)
python prop_migration/run_basis_batch.py --min-freq 332 --delay 1

# Next tiers
python prop_migration/run_basis_batch.py --min-freq 80  --max-freq 331 --delay 1
python prop_migration/run_basis_batch.py --min-freq 19  --max-freq 79  --delay 1
python prop_migration/run_basis_batch.py --min-freq 1   --max-freq 18  --delay 1
```

The batch runner skips already-done bases (done_guids ≥ tsv_freq) and sleeps 50 min
on consecutive failures to survive the daily FactGrid maintenance window (7pm ET).

---

## Locator bases (DHEE page numbers etc.)

757 vetted=Y bases have a `loc` field (5,533 GUIDs total). The majority are DHEE page
numbers (182 bases, 3,275 GUIDs, all `loc_type=page` → P54).

**Do a single-item pilot on a DHEE base before running in bulk:**

```bash
python prop_migration/apply_basis_migration.py --basis "DHEE 2400" --item <qid> --delay 1
```

Unmapped loc types (skip until confirmed with Charles):
- `volume` (e.g. "Arteaga I:286") — no FactGrid property assigned
- `annotation` (e.g. "BNE Cat.: sello") — no FactGrid property assigned

---

## Progress log

The script appends a JSONL record to `prop_migration/basis_migration_progress.jsonl`
for every successfully converted statement GUID. Each run is fully resumable:
re-running the same `--basis` command skips already-converted GUIDs automatically.

To inspect the most recent entry:

```bash
tail -1 prop_migration/basis_migration_progress.jsonl | jq .

# Fields useful for verifying a change (item as URL):
tail -1 prop_migration/basis_migration_progress.jsonl | jq '{item: ("https://database.factgrid.de/wiki/" + .item), prop, main_value, basis, qid}'
```

To see overall progress:

```bash
python - <<'EOF'
import json, csv

done = {}
with open('prop_migration/basis_migration_progress.jsonl') as f:
    for line in f:
        try:
            r = json.loads(line)
            done[r['basis']] = done.get(r['basis'], 0) + 1
        except: pass
print(f'{len(done)} distinct basis values converted, {sum(done.values()):,} total GUIDs')
EOF
```
