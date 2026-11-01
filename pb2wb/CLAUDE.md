# PhiloBiblon FactGrid Migration — pb2wb

## Project background
PhiloBiblon is a UC Berkeley bibliography project for medieval Iberian texts.
We migrated a legacy database to a Wikibase instance called FactGrid
(https://database.factgrid.de). The main migration pipeline (described in
README.md) is now complete.

## Current task: string property → item property migration
During migration, several properties were created as string-valued as a
temporary measure. We now need to replace these with their item-valued
counterparts. The property pairs are:

| String property | Item property | Usage |
|---|---|---|
| P1141 * Place of publication | P241 | Place of publication |
| P1134 * Creator | P845 | Authors, editors, translators |
| P1136 * Associated person | P703 | Editors, collaborators |
| P1137 * Published in | P64 | Publication containing an article |
| P1140 * Publisher | P206 | Publisher/publishing house |

We are starting with P1141 → P241 (places) as a pilot because place items
already exist in FactGrid and require less item creation.

## Two distinct implementation paths

These migrations fall into two categories with different tooling:

| Category | Properties | Tool | Reason |
|---|---|---|---|
| Main-value property swap | P1141, P1134, P1136, P1137, P1140 | QuickStatements | Add new item-valued statement, delete old string-valued statement — QS handles this natively |
| Qualifier → reference conversion | P721 | Wikibase API | Moving data from qualifier section to reference section of an existing statement — QS has no syntax for this |

QuickStatements is preferred when possible: it is simpler, auditable, and
requires no API code. The Wikibase API is used only where QuickStatements
cannot express the operation.

## Workflow (three phases)
1. **Generate**: SPARQL query to get all distinct string values, attempt
   automatic matching to FactGrid items, output a candidate mapping TSV
2. **Vet**: Colleague reviews/corrects mapping in Google Sheets
3. **Implement**: Read vetted mapping, apply changes via QuickStatements
   (main-value swaps) or Wikibase API (qualifier→reference conversions)

## Technical conventions
- Always run from pb2wb/ as CWD
- Use WBManager from common/wb_manager.py for SPARQL queries and API writes
- See util/run_simple_sparql.py for the established query pattern
- Settings (endpoint, credentials) in common/settings.py — never commit credentials
- QuickStatements format: one command per line, e.g. Q123|P241|Q456
- For deletion: Q123|-P1141|"string value"
- New code for this task lives in pb2wb/prop_migration/

## Key people
- Max: does the coding and automation
- Charles (retired UCB Spanish prof): domain expert, vets mappings manually
  in Google Sheets, does not need to understand QIDs directly

---

## Current state (as of April 2026)

### Completed: P1141 → P241 place migration (prop_migration/)

The three-phase workflow (generate → vet → implement) is built and partially
complete. Phase 3 (QuickStatements generation) not yet started.

#### Files in prop_migration/
| File | Purpose |
|------|---------|
| `generate_place_mapping.py` | SPARQL query to extract distinct P1141 strings |
| `fill_gaps.py` | Searches FactGrid wbsearchentities API per string; optional Ollama LLM for compound splitting (--llm) and fuzzy-match verification (--llm-verify) |
| `merge_candidates.py` | Merges API results into the sheet TSV, adds auto_match and vetted columns |
| `sync_sheet.py` | Pushes/pulls data to/from Google Sheets via service account; matches rows by compound key (column A, column C); never overwrites rows where column I = Y |
| `README.md` | Summary of prop_migration workflow and current state |
| `test_fill_gaps.py` | 41 pytest unit tests |
| `vetting_p1141.md` | Instructions for Charles |

#### Key design decisions
- Match rows to Google Sheet by compound key (col A, col C) — never by row
  position, Charles may have sorted the sheet
- vetted column: Y = human-approved, auto = high-confidence automatic match,
  blank = needs review
- Correcting column F without marking Y will be overwritten on next run
- Compound place strings (e.g. "Como - Pavia") split into one row per city
- Uses wbsearchentities API for matching, Ollama for fuzzy verification
- Anthropic API with prompt caching stubbed for future use

#### Match types
api_label, api_label_stripped, api_alias, api_alias_stripped, api_fuzzy,
latin_lookup, corrections, sheet, rejected, compound, none

#### Latest run stats
557 distinct strings: 450 matched, 107 unmatched. Sheet has 1084 rows
(compounds expand row count). Charles vetting in progress.

---

### In progress: P721 basis/reference migration (prop_migration/)

#### Key files
| File | Purpose |
|------|---------|
| `fetch_basis_values.py` | SPARQL query to extract all distinct P721 strings with frequencies |
| `generate_basis_mapping.py` | Main pipeline: preprocess → known_qids lookup → API search → LLM parse → candidates TSV |
| `known_qids.tsv` | Manually curated key→QID mappings (~500 entries); single source of truth for API misses |
| `bne_shelfmark_candidates.tsv` | 407 BNE MSS/ shelfmark QIDs found via SPARQL STRSTARTS; review before adding to known_qids |
| `lookup_bne_shelfmarks.py` | SPARQL lookup for BNE manuscript shelfmarks using Spanish label prefix matching |
| `lookup_surname_refs.py` | SPARQL lookup for single-surname keys via PhiloBiblon BIBID aliases |
| `apply_basis_migration.py` | Applies P721→P129 conversion to FactGrid via Wikibase API |
| `sync_sheet.py` | Push/pull Google Sheets for p721 and p1141 pipelines |
| `match_type_report.py` | Summary report of basis_candidates.tsv by match_type |
| `test_generate_basis_mapping.py` | Unit tests for generate_basis_mapping.py helpers |
| `vetting_p721.md` | Instructions for Charles on how to vet the P721 sheet |
| `vetting_p1141.md` | Instructions for Charles on how to vet the P1141 place sheet |

P721 is a string-valued **qualifier** (prefix pq:, not wdt:) used across all
PhiloBiblon tables to record the source/basis of statements. Goal is to convert
to structured references: P129 (According to, item-valued) + optional locator
qualifiers P54 (pages), P100 (folio), P90 (number).

#### Scale
- 132,259 total P721 usages
- 17,004 distinct strings
- Top ~50 values cover majority of usages — start there

#### Pre-processing rules (before FactGrid search)
- Strip HTML tags: `<i>IGM</i>` → `IGM`
- Exclude non-references: `fol. mod.`, `fol. ant.`, `ant.`, `mod.`, `[?]`,
  `?`, `princeps`, `fol. antiga`, `fol. manuscrita` and similar
- Flag compound references containing ` / ` — skip search, manual handling
- DHEE + number pattern: split into key=`DHEE`, loc=number
- Author + 4-digit year (e.g. "Hernández 2006"): key=whole string, loc=empty
- Author + year + colon + number (e.g. "Beltrán 1997:60"): key="Beltrán 1997",
  loc="60"
- Roman numeral volume + page (e.g. "Arteaga I:286"): key="Arteaga", loc="I:286"
- Trailing footnote indicator (e.g. "27n"): loc_type=footnote
- Folio patterns (f. 93v, 244v, 3r): loc_type=folio

#### Output TSV columns
freq, basis (original), key (parsed), loc, loc_type, match_type, qid, label

#### LLM strategy
- Use Anthropic API (not Ollama) for parsing ambiguous citation strings
- Use prompt caching on system prompt (contains citation rules + few-shot examples)
- Scope initial run to top 200 distinct values only

#### Known non-trivial cases from top 200
- `Faulhaber` (21531) — person, QID exists
- `<i>IGM</i>` (5708) — titled work
- `<i>DHEE</i> 1875` etc. — same work, different page numbers
- `BNE MSS/7811` etc. — institution + shelfmark
- `fol. mod.` (1071) — excluded, not a reference
- `<i>IGM</i> / Faulhaber` (64) — compound, manual handling
- `Rodríguez x` (80) — roman numeral page, ambiguous author

#### Implementation: qualifier → reference conversion

**QuickStatements cannot do this.** QS can create new statements with
references, but has no syntax for adding a reference to a pre-existing
statement. This requires the Wikibase API directly.

The atomic unit of work for each affected statement is:
1. Fetch the item
2. Find the statement by GUID
3. Add a reference: P129 = QID (and optionally P54/P100/P90 for locator)
4. Remove the P721 qualifier from that statement
5. Write back

Step 3 must always precede step 4 so source information is never lost if
something fails midway.

**Concrete example**: Q425307 has ~170 Author statements each with qualifier
P721 = "Perea 2004". Each becomes a reference P129 = Q1071227. This pattern
repeats 942 times across the dataset for this one value alone.

**wb_manager.py**: all three statement-mutation methods are implemented:

| Method | Purpose |
|--------|---------|
| `get_statements_with_qualifier(item_id, qual_prop, qual_value)` | Returns list of (guid, main_prop, main_value) for all matching statements |
| `add_reference_to_statement(item_id, guid, ref_prop, ref_qid)` | Adds a reference block to an existing statement |
| `remove_qualifier_from_statement(item_id, guid, qual_prop, qual_value)` | Removes a qualifier from an existing statement |

---

### Pending: remaining property pair migrations

| String prop | Item prop | Usage | Status |
|-------------|-----------|-------|--------|
| P1141 * Place of publication | P241 | Place of publication | Phase 2 (vetting) |
| P1134 * Creator | P845 | Authors, editors, translators | Not started |
| P1136 * Associated person | P703 | Editors, collaborators | Not started |
| P1137 * Published in | P64 | Publication containing an article | Not started |
| P1140 * Publisher | P206 | Publisher/publishing house | Not started |
| P721 * Basis (qualifier) | P129 + locators | Source of statements | In progress |

---

## Infrastructure

### Google Sheets integration (gspread)
- Service account auth (JSON key file)
- Sheet ID and credentials path in common/settings.py or .env
- Never commit credentials; credentials file in .gitignore
- Push: update in place by compound key, preserve formatting
- Pull: read sheet to local TSV

### wb_manager.py
- Read: `runSparQlQuery()` for all SPARQL queries
- Write (entity creation): `create_wb_p()`, `get_or_create_wb_p()`, `create_wb_q()`
- Write (statement mutation): `get_statements_with_qualifier()`,
  `add_reference_to_statement()`, `remove_qualifier_from_statement()` — implemented

### QuickStatements
Used for main-value property swaps (P1141 and the other four pairs). Cannot
add references to existing statements — use the API for that.

Format:
- Add item-valued statement: `Q123|P241|Q456`
- Delete string-valued statement: `Q123|-P1141|"string value"`

### Conventions
- Always run from pb2wb/ as CWD
- Settings in common/settings.py — never commit credentials
- New code in pb2wb/prop_migration/
