# Property migration: string → item

During the original migration several properties were created as string-valued
as a temporary measure. This directory contains scripts to replace them with
their item-valued counterparts.

The pilot is **P1141 (string: place of publication) → P241 (item)**, chosen
because place items already exist in FactGrid and require no new item creation.

For general environment setup (Python version, virtualenv, `common/settings.py`)
see the [top-level README](../README.md).

All scripts are run from `pb2wb/` as CWD.

---

## Setup

### Google Sheets credentials

The pipeline syncs with a Google Sheet that Charles vets manually.

1. In Google Cloud Console, create a service account with the **Google Sheets**
   and **Google Drive** APIs enabled. Download the JSON key file and store it
   somewhere outside the repo (e.g. `~/.config/pb2wb/service-account.json`).
2. Share the target Google Sheet with the service account's `client_email`
   address as **Editor**.
3. Add to `.qs_env` (never commit):

```
GSHEETS_CREDENTIALS_PATH=/path/to/service-account.json
P1141_SHEET_ID=<sheet ID from the Google Sheet URL>
```

`.qs_env` is loaded automatically by `sync_sheet.py`.

---

## Full pipeline

```bash
# 1. Pull Charles's current sheet from Google Sheets
python prop_migration/sync_sheet.py pull
#    writes: prop_migration/P1141-P241.tsv

# 2. Match each place string to a FactGrid QID via the wbsearchentities API
python prop_migration/fill_gaps.py --llm --llm-verify
#    reads:  prop_migration/P1141-P241.tsv
#    writes: prop_migration/place_candidates.tsv

# 3. Merge candidates back into the sheet, adding auto_match and vetted columns
python prop_migration/merge_candidates.py
#    reads:  prop_migration/place_candidates.tsv
#            prop_migration/P1141-P241.tsv
#    writes: prop_migration/sheet_updated.tsv

# 4. Push to Google Sheets (dry-run first)
python prop_migration/sync_sheet.py push --dry-run
python prop_migration/sync_sheet.py push
#    reads:  prop_migration/sheet_updated.tsv
#    writes: Google Sheet (columns P241 Qid, P241_values, auto_match, vetted only)
```

After Charles vets the sheet, pull again and re-run from step 2 to pick up
his corrections. Repeat until Charles is satisfied, then proceed to Phase 3
(QuickStatements generation — not yet implemented).

---

## Script reference

### `sync_sheet.py`

```
python prop_migration/sync_sheet.py pull [--worksheet TAB]
python prop_migration/sync_sheet.py push [--worksheet TAB] [--dry-run]
```

- **pull** downloads the sheet to `prop_migration/P1141-P241.tsv`. This is a
  safe default name that does not overwrite any manually maintained file.
- **push** updates only the columns we own (P241 Qid, P241_values, auto_match,
  vetted). Rows where `vetted` is already `Y` in the sheet are never touched.
  Compound-split rows (one source string → multiple cities) insert new rows
  into the sheet rather than overwriting.
- `--worksheet` overrides the default tab name (`P1141-P241`), useful if
  Charles adds or renames tabs.

### `fill_gaps.py`

Searches the FactGrid `wbsearchentities` API to find a QID for each distinct
place string.

```
python prop_migration/fill_gaps.py [options]

  --sheet PATH       Input sheet TSV (default: prop_migration/P1141-P241.tsv)
  --out PATH         Output candidates TSV (default: prop_migration/place_candidates.tsv)
  --llm              Use local Ollama to split compound place strings
  --llm-verify       Use local Ollama to verify fuzzy matches geographically
  --llm-model NAME   Ollama model (default: llama3.2)
  --limit N          Process only top N strings (for testing)
  --dry-run          Show what would be searched without calling the API
```

**match_type values in output:**

| match_type | meaning | vetted |
|---|---|---|
| `api_label` / `api_alias` | exact match on FactGrid label or alias | `auto` |
| `latin_lookup` | known Latin place name → modern equivalent | `auto` |
| `sheet` | already in Charles's mapping | `Y` |
| `api_label_stripped` / `api_alias_stripped` | matched after stripping qualifier (", PA", "[Mass]") | blank — VERIFY |
| `api_fuzzy` | text differs from query; LLM-verified survivors | blank — VERIFY |
| `corrections` | manual override dict | blank — VERIFY |
| `compound` | multi-city string, split by LLM into one row per city | blank |
| `none` | no match found; place may not exist in FactGrid yet | blank |

### `merge_candidates.py`

Merges `place_candidates.tsv` back into the sheet TSV, populating columns
P241 Qid, P241_values, auto_match, and vetted. Compound strings with
LLM-resolved parts are expanded into one row per city.

```
python prop_migration/merge_candidates.py [options]

  --candidates PATH  (default: prop_migration/place_candidates.tsv)
  --sheet PATH       (default: prop_migration/P1141-P241.tsv)
  --out PATH         (default: prop_migration/sheet_updated.tsv)
```

---

## Vetting protocol

See [`vetting.md`](vetting.md) for the instructions given to Charles.

**How iteration works:**

- Rows where `vetted = auto` were matched with high confidence; Charles can
  spot-check but does not need to review them.
- Rows where `vetted` is blank need Charles's attention. He confirms or
  corrects column F and types `Y` in the vetted column.
- He may correct place name spellings in column C at any time; these are
  picked up automatically on the next `fill_gaps.py` run.
- He can return the sheet at any point — he does not need to finish all rows
  before we run another iteration.

On re-run, `fill_gaps.py` trusts all rows where `vetted` is `Y` or `auto`
and re-processes everything else (blank-vetted rows and any new strings).
If the sheet has no `vetted` column at all (original bootstrap sheet), all
column F values are trusted.

---

## Working files (untracked)

| File | Created by | Purpose |
|---|---|---|
| `P1141-P241.tsv` | `sync_sheet.py pull` | Charles's sheet, local copy |
| `place_candidates.tsv` | `fill_gaps.py` | Per-string QID candidates |
| `sheet_updated.tsv` | `merge_candidates.py` | Ready to push to Google Sheets |
