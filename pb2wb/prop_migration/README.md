# Property migration: string → item

During the original migration several properties were created as string-valued
as a temporary measure. This directory contains scripts to replace them with
their item-valued counterparts.

Two migrations are documented here:

- **P1141 → P241** (place of publication): pilot; place items already exist in
  FactGrid and require no new item creation. *(Phase 2: vetting in progress.)*
- **P721 → P129 + locators** (basis/reference qualifier): converts free-text
  citation strings to structured references. *(Phase 2: vetting in progress; pilot migrations executed.)*

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

#### The legacy seed and what to trust

`Reference sources.xlsx` was created by Max and shared with Charles for manual review.
Charles edited some rows (correcting `key`, `loc`, or adding a `Comment`).
**Only those edits are ground truth.** Rows Charles left unchanged may have been implicitly
accepted, or may never have been reviewed — there is no way to tell from the file alone.

The Google Sheets version history of the Reference Sources sheet is the authoritative
record of which rows Charles actually changed. Before re-seeding from this file, extract
the diff between the original upload and Charles's edited version; use only the diffed rows
as `legacy` seeds. Treat unchanged rows as unvetted candidates for the normal pipeline.

### Iterative fill-gaps (after bootstrap)

```bash
# 1. Pull Charles's current sheet from Google Sheets
python prop_migration/sync_sheet.py --pipeline p721 pull
#    writes: prop_migration/P721-P129.tsv

# 2. Re-search all unvetted rows
python prop_migration/generate_basis_mapping.py                                    # rule-based only
python prop_migration/generate_basis_mapping.py --llm                              # LLM via litellm (default: gemini/gemini-2.0-flash)
python prop_migration/generate_basis_mapping.py --llm --llm-model anthropic/claude-haiku-4-5-20251001  # specify model
#    reads:  prop_migration/P721-P129.tsv
#    writes: prop_migration/basis_candidates.tsv

# 3. Push candidates to Google Sheets (dry-run first)
python prop_migration/sync_sheet.py --pipeline p721 push --dry-run
python prop_migration/sync_sheet.py --pipeline p721 push
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
`footnote` (e.g. `27n`), `page` (plain number or range), `volume` (e.g. `I:286`).
If the LLM detects a locator but cannot determine the type, it uses `llm_guess`.

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

| match_type | meaning | confidence |
|---|---|---|
| `charles_edit` | row Charles manually edited in the Reference Sources sheet — ground truth | high |
| `known` | manually curated entry in `known_qids.tsv` | high |
| `api_label` / `api_alias` | exact match on FactGrid label or alias | high |
| `api_fuzzy` | API hit but matched text differs from key | medium — VERIFY |
| `shelfmark` | BNE/BNM shelfmark pattern — no FG search attempted | low — needs lookup |
| `bnm_norm` | BNM NNNN normalised to BNE MSS/NNNN | medium |
| `excluded` | non-reference string (fol. mod., ?, princeps …), not searched | — |
| `compound` | contains ` / `; needs manual splitting | — |
| `none` | no match found | blank |
| `llm_pending` | LLM was called but returned no usable parse | blank |
| `llm_guess` | LLM inferred a loc but was uncertain about loc_type — Charles should review | blank — VERIFY |

### Supplementary lookup tools

These are run manually when the main pipeline leaves gaps.

```bash
# Find FactGrid items for reference works matched by surname prefix
python prop_migration/lookup_surname_refs.py

# Resolve BNE shelfmark strings (BNE MSS/NNNN) to QIDs
python prop_migration/lookup_bne_shelfmarks.py

# Print match_type distribution and top unmatched rows
python prop_migration/match_type_report.py

# One-time: extract Charles's gold edits from Reference Sources sheet history
python prop_migration/extract_gold_seed.py
```

Results from the first two feed into `known_qids.tsv` for the next pipeline run.

### Working files (untracked)

| File | Created by | Purpose |
|---|---|---|
| `P721-raw-values.tsv` | `fetch_basis_values.py` | Raw (value, freq) pairs from FactGrid SPARQL |
| `P721-parsed.tsv` | `parse_basis_values.py` | Rule-parsed key + loc (no QIDs) |
| `P721-P129-seed.tsv` | `lookup_basis_keys.py` | Initial seed to upload to Google Sheets |
| `P721-P129.tsv` | `sync_sheet.py pull` | Charles's sheet, local copy |
| `basis_candidates.tsv` | `generate_basis_mapping.py` | Per-string QID candidates, ready to push |
| `Reference sources.xlsx` | downloaded manually | Legacy QID map from Charles's prior work |
| `reference_source.gold_seed.tsv` | `extract_gold_seed.py` | Charles's confirmed edits only |
| `.llm_ckpt.{model}.{hash}.tsv` | `generate_basis_mapping.py --llm` | LLM parse cache; one file per model+prompt |
| `.llm_ckpt.{model}.{hash}.meta` | same | Human-readable JSON: model name, prompt preview, cache key |
| `.api_ckpt.tsv` | `generate_basis_mapping.py` | FactGrid API search cache; shared across models |

### tracked working files

| File | Purpose |
|---|---|
| `known_qids.tsv` | Manually curated QID mappings for strings the API misses |

---

## P721 → P129 implementation

The other property migrations (P1141 → P241, P1134 → P845, etc.) will be
implemented via QuickStatements, which handles add/delete of statement values
natively. P721 requires the Wikibase API directly because QuickStatements has
no syntax for adding a reference to a *pre-existing* statement — it can only
create new statements with references attached.

Once a basis string has a vetted QID in `basis_candidates.tsv`, use
`apply_basis_migration.py` to convert the matching P721 qualifiers to P129
references in FactGrid via the Wikibase API.

### How it works

For each targeted `(basis_string, p129_qid)` pair the script:

1. Runs a SPARQL query to find all items carrying `pq:P721 = basis_string`
2. For each item, fetches it once, then for every matching statement:
   - Adds a reference: `P129 = qid` (plus a locator qualifier if `loc` is set)
   - Removes the `P721` qualifier
3. Writes the item once (all changes batched per item)

**Locator property mapping:**

| loc_type | FactGrid property |
|---|---|
| `page` | P54 (Page(s)) |
| `folio` | P100 (Folio(s)) |
| `number` | P90 (Number) |
| `footnote` | P90 — *pending confirmation from Charles; existing data uses P54* |
| `volume` | *not yet mapped — pending confirmation from Charles* |

### Usage

Edit the `CASES` dict at the top of `apply_basis_migration.py` to add the
basis strings you want to migrate:

```python
CASES = {
    'Faulhaber':        {'qid': 'Q164508'},
    'Perea 2004':       {'qid': 'Q1071227'},
    '<i>DHEE</i> 2400': {'qid': 'Q426064', 'loc': '2400', 'loc_type': 'page'},
}
```

Then:

```bash
# Dry run (default) — shows what would change, writes nothing
python prop_migration/apply_basis_migration.py --basis "Faulhaber" --item Q1086703

# Restrict to one item for a pilot
python prop_migration/apply_basis_migration.py --basis "Perea 2004" --item Q425307 --execute

# Run across all items with that basis value
python prop_migration/apply_basis_migration.py --basis "Faulhaber" --execute
```

The `--item` flag is recommended for initial testing. Omit it only once you
are confident in the QID mapping.
