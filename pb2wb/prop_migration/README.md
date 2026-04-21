# Property migration: string → item

During the original migration several properties were created as string-valued
as a temporary measure. This directory contains scripts to replace them with
their item-valued counterparts.

Two migrations are documented here:

- **P1141 → P241** (place of publication): pilot; place items already exist in
  FactGrid and require no new item creation. *(Phase 2: vetting in progress.)*
- **P721 → P129 + locators** (basis/reference qualifier): converts free-text
  citation strings to structured references. *(Phase 1: bootstrapping.)*

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
P721_SHEET_ID=<sheet ID for the P721-P129 sheet>
```

`.qs_env` is loaded automatically by `sync_sheet.py`.

---

## P1141 → P241 pipeline (place of publication)

### Full pipeline

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

### Script reference

#### `sync_sheet.py`

```
python prop_migration/sync_sheet.py pull [--worksheet TAB]
python prop_migration/sync_sheet.py push [--worksheet TAB] [--dry-run]
```

- **pull** downloads the sheet to `prop_migration/P1141-P241.tsv`.
- **push** updates only the columns we own (P241 Qid, P241_values, auto_match,
  vetted). Rows where `vetted` is already `Y` are never touched.
  Compound-split rows insert new rows rather than overwriting.
- `--worksheet` overrides the default tab name (`P1141-P241`).

#### `fill_gaps.py`

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
| `api_label_stripped` / `api_alias_stripped` | matched after stripping qualifier | blank — VERIFY |
| `api_fuzzy` | text differs from query; LLM-verified survivors | blank — VERIFY |
| `corrections` | manual override dict | blank — VERIFY |
| `compound` | multi-city string, split by LLM into one row per city | blank |
| `none` | no match found; place may not exist in FactGrid yet | blank |

#### `merge_candidates.py`

Merges `place_candidates.tsv` back into the sheet TSV, populating columns
P241 Qid, P241_values, auto_match, and vetted. Compound strings with
LLM-resolved parts are expanded into one row per city.

```
python prop_migration/merge_candidates.py [options]

  --candidates PATH  (default: prop_migration/place_candidates.tsv)
  --sheet PATH       (default: prop_migration/P1141-P241.tsv)
  --out PATH         (default: prop_migration/sheet_updated.tsv)
```

### Vetting protocol

See [`vetting.md`](vetting.md) for the instructions given to Charles.

**How iteration works:**

- Rows where `vetted = auto` were matched with high confidence; Charles can
  spot-check but does not need to review every one.
- Rows where `vetted` is blank need Charles's attention. He confirms or
  corrects column F and types `Y` in the vetted column.
- He may correct place name spellings in column C at any time; these are
  picked up automatically on the next `fill_gaps.py` run.

On re-run, `fill_gaps.py` trusts all rows where `vetted` is `Y` or `auto`
and re-processes everything else. If the sheet has no `vetted` column at all
(original bootstrap), all column F values are trusted.

### Working files (untracked)

| File | Created by | Purpose |
|---|---|---|
| `P1141-P241.tsv` | `sync_sheet.py pull` | Charles's sheet, local copy |
| `place_candidates.tsv` | `fill_gaps.py` | Per-string QID candidates |
| `sheet_updated.tsv` | `merge_candidates.py` | Ready to push to Google Sheets |

---

## P721 → P129 pipeline (basis/reference qualifier)

P721 is a string-valued qualifier used across all PhiloBiblon tables to record
the source of statements. Goal: convert to structured references using P129
(*According to*, item-valued) plus optional locator qualifiers P54 (pages),
P100 (folio), P90 (number).

**Scale:** ~130k P721 usages, ~16k distinct strings. The initial run covers
the top 200 by frequency.

### Bootstrap (run once)

The bootstrap is split into three steps so each concern can be re-run independently:

| Step | Script | Network | Re-run when |
|---|---|---|---|
| 0 | `fetch_basis_values.py` | FactGrid SPARQL | fresh data needed |
| 1 | `parse_basis_values.py` | none | tuning parse rules |
| 2 | `lookup_basis_keys.py` | FactGrid API | after re-parse |

```bash
# Step 0: pull all distinct P721 values from FactGrid (slow; keep the output)
python prop_migration/fetch_basis_values.py
#    writes: prop_migration/P721-raw-values.tsv
#
#   --limit N   cap rows fetched (default: no limit)
#   --out PATH  output path (default: prop_migration/P721-raw-values.tsv)

# Step 1: parse raw values into key + loc + col_* columns (no network)
python prop_migration/parse_basis_values.py --dry-run   # inspect first
python prop_migration/parse_basis_values.py
#    reads:  prop_migration/P721-raw-values.tsv
#    writes: prop_migration/P721-parsed.tsv
#
#   --values PATH  raw TSV (default: prop_migration/P721-raw-values.tsv)
#   --out PATH     parsed TSV (default: prop_migration/P721-parsed.tsv)
#   --limit N      top N values only (default: all)

# Step 2: search FactGrid for each unique key, write seed TSV
python prop_migration/lookup_basis_keys.py --dry-run    # check counts first
python prop_migration/lookup_basis_keys.py
#    reads:  prop_migration/P721-parsed.tsv
#            prop_migration/Reference sources.xlsx  (optional legacy QID map)
#    writes: prop_migration/P721-P129-seed.tsv
#
#   --parsed PATH  parsed TSV (default: prop_migration/P721-parsed.tsv)
#   --out PATH     seed TSV (default: prop_migration/P721-P129-seed.tsv)
#   --xlsx PATH    legacy xlsx (default: prop_migration/Reference sources.xlsx)
#   --no-xlsx      skip legacy xlsx seeding
```

Then upload `P721-P129-seed.tsv` to Google Sheets as the initial P721-P129 sheet.

`generate_basis_seed.py` still works as a single-pass shortcut (steps 1+2 combined)
but the three-step flow above is preferred when iterating on parse logic.

### Iterative fill-gaps (after bootstrap)

```bash
# 1. Pull Charles's current sheet from Google Sheets
python prop_migration/sync_sheet.py pull --worksheet P721-P129
#    writes: prop_migration/P721-P129.tsv

# 2. Re-search all unvetted rows
python prop_migration/generate_basis_mapping.py          # rule-based only
python prop_migration/generate_basis_mapping.py --llm    # also parse llm_pending via Anthropic
#    reads:  prop_migration/P721-P129.tsv
#    writes: prop_migration/basis_candidates.tsv

# 3. Push candidates to Google Sheets (dry-run first)
python prop_migration/sync_sheet.py push --worksheet P721-P129 --dry-run
python prop_migration/sync_sheet.py push --worksheet P721-P129
#    reads:  prop_migration/basis_candidates.tsv
#    writes: Google Sheet (qid, label, match_type, vetted columns only)
```

Repeat after each vetting round until Charles is satisfied.

### Pre-processing pipeline

Applied to each raw P721 string before API search (in order):

| rule | example input | key | loc |
|---|---|---|---|
| `excluded` | `fol. mod.`, `?`, `princeps` | — | — |
| `compound` | `Faulhaber / IGM` | — | — |
| `dhee` | `DHEE 1875` | `DHEE` | `1875` |
| `auth_year_loc` | `Beltrán 1997:60` | `Beltrán 1997` | `60` |
| `roman_vol` | `Arteaga I:286` | `Arteaga` | `I:286` |
| `auth_year` | `Hernández 2006` | `Hernández 2006` | — |
| `raw` | `Faulhaber` | `Faulhaber` | — |

HTML tags are stripped before classification (`<i>IGM</i>` → `IGM`).

`loc_type` is inferred from the locator: `folio` (e.g. `93v`, `f. 3r`),
`footnote` (e.g. `27n`), `page` (plain number or range).

### API search and disambiguation

`generate_basis_mapping.py` fetches up to 5 candidates per key from
`wbsearchentities`. When multiple exact matches are found, a second
`wbgetentities` call checks for PhiloBiblon BIBID aliases
(`BETA bibid NNN`, `BITAGAP bibid NNN`, `BITECA bibid NNN`) to disambiguate
reference works from persons or places with the same label. Among exact
matches, preference order is:

1. Item confirmed to have a BIBID alias
2. Item whose description contains bibliographic keywords (*reference*,
   *bibliography*, *critical edition*, *scholarly*, *obra*, *trabajo*)
3. First exact match returned by the API

### match_type values

| match_type | meaning | vetted |
|---|---|---|
| `legacy` | QID taken from legacy `Reference sources.xlsx` | blank — VERIFY |
| `api_label` / `api_alias` | exact match on FactGrid label or alias | `auto` |
| `api_fuzzy` | API hit but matched text differs from key | blank — VERIFY |
| `excluded` | non-reference string, not searched | — |
| `compound` | contains ` / `; needs manual splitting | blank |
| `none` | no match found; known parse pattern | blank |
| `llm_pending` | no match found; raw string, Anthropic parse not yet run | blank |
| `vetted` | row already vetted in sheet; passed through unchanged | preserved |

### Working files (untracked)

| File | Created by | Purpose |
|---|---|---|
| `P721-raw-values.tsv` | `fetch_basis_values.py` | Raw (value, freq) pairs from FactGrid SPARQL |
| `P721-parsed.tsv` | `parse_basis_values.py` | Rule-parsed key + loc + col_* (no QIDs) |
| `P721-P129-seed.tsv` | `lookup_basis_keys.py` | Initial seed to upload to Google Sheets |
| `P721-P129.tsv` | `sync_sheet.py pull` | Charles's sheet, local copy |
| `basis_candidates.tsv` | `generate_basis_mapping.py` | Per-string QID candidates |
| `Reference sources.xlsx` | downloaded manually | Legacy QID map from Charles's prior work |
