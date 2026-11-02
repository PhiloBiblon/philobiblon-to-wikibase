# Source-Citation Mapping (P721→P129) — Notes for Charles

I've created a new spreadsheet for P721 "basis" strings. It's ready for you to review and improve.

Each basis
string identifies the work or resource that was consulted. I've matched as many
as I can automatically; I'm asking you to review and fill gaps.

The sheet tab is **P721-P129**.

---

## Columns of interest

| Column | Name | What it contains |
|--------|------|-----------------|
| A | freq | How many times this basis string appears in the database — read only |
| B | basis | The original P721 string — **do not edit** |
| C | key | The searchable part I extracted from the basis (e.g. "Beltrán 1997" from "Beltrán 1997:60") |
| D | match_type | How I found the match — read only, set automatically |
| E | qid | FactGrid item QID — the main thing to correct |
| F | label | Plain-text label of that item — read only |
| G | vetted | Your judgment — **please populate this** |
| H | loc_type | Type of locator: page, folio, footnote, volume, or blank |
| I | loc | Locator value extracted from the basis string (e.g. "60", "93v") |

**Please note**: If you correct any cell, mark column G as `Y` in the same row.
Otherwise your correction may be overwritten the next time I run the script.
For every row you touch: fix what's wrong, then mark `Y` in column G.

---

## Column G — your judgment

| Value | Meaning |
|-------|---------|
| `Y` | You've reviewed it and are happy with the QID in column E |
| *(blank)* | Needs your attention or hasn't been reviewed yet |

Rows already marked `Y` won't be touched by the script — they're locked.

---

## Column D — how I found the match

| Value | Meaning |
|-------|---------|
| `vetted` | You previously marked this `Y` — carried forward unchanged |
| `known` | QID comes from a curated list I maintain — high confidence |
| `api_label` | Exact FactGrid label match — high confidence |
| `api_alias` | Exact FactGrid alias match — high confidence |
| `api_fuzzy` | FactGrid returned a hit but the label differs from my search key — **please review** |
| `none` | Nothing found in FactGrid — if you know the item, please add the QID |
| `excluded` | Not a bibliographic reference (e.g. "fol. mod.", "?") — no action needed |
| `shelfmark` | Library call number — not yet matched |
| `llm_pending` | Couldn't parse the string automatically — rare |

The `api_fuzzy` rows (about 2,900) are the ones most in need of your attention.
The match may be correct or it may be the wrong work by the same author —
please check and mark `Y` if satisfied.

---

## What you can and cannot edit

**Edit freely** (but mark `Y` when done):
- Column E (qid) — enter the correct FactGrid QID if mine is wrong or missing
- Column C (key) — correct the search key if I extracted it wrong
- Column H (loc_type) and I (loc) — correct the locator type or value if wrong
- Column G (vetted) — mark `Y` to lock a row

**Do not edit**:
- Column B (basis) — this is the raw database string and is used to match rows back; changing it will cause data loss
- Column A (freq) — read-only count
- Column D (match_type) and F (label) — set automatically by the script

---

## The `none` rows

About 10,900 rows have no match. Many of these are scholarly works that simply
aren't yet in FactGrid. If you recognise a reference, please add the QID in
column E and mark `Y`. If you can't find it or it doesn't exist yet, you can
leave column E blank and still mark `Y` — that tells me you've seen it and
it's not findable for now.

---

## Updates and iteration

I can re-run the reconciliation at any time to pick up newly added FactGrid
items or corrections I've made to the matching rules. Rows marked `Y` won't
be touched.

---

# Place-of-Publication Mapping — Notes for Charles

You asked me to populate column F (P241 Qid) with FactGrid place items matching
the place strings in column C. I've done that, and also added two new columns:
H (auto_match) and I (vetted). Column H explains how I found each match.
I'm asking you to record your judgment in column I.

---

## Columns of interest

| Column | Name | Contents |
|--------|------|----------|
| A | (item ID) | PhiloBiblon item identifier |
| C | _Place_of_publication | Place string as it appears in the database |
| F | P241 Qid | FactGrid place item (what you asked me to fill) |
| G | P241_values | Plain-text label of that item |
| H | auto_match | How I found the match |
| I | vetted | Your judgment — please populate this |

I started from [your spreadsheet](https://docs.google.com/spreadsheets/d/1tJmro7H-eH2LhMugzw30USNV4r7B8yR_KpdAUmlfELE/edit?gid=6214243#gid=6214243)
Where there was already a value in column F, I've left the entire row alone and pre-populated column I with `Y`.

---

## Column H — how I found the match

| Value | Meaning |
|-------|---------|
| *(blank)* | Exact match on FactGrid label or known alias — high confidence |
| `stripped qualifier — VERIFY` | Matched after stripping something like ", OR" or "[Mass]" — please check |
| `VERIFY` | Slight name difference — lower confidence |
| `compound — split (City)` | One city from a multi-city string — see below |
| `compound — needs split` | Couldn't split automatically |
| `no match found` | Nothing in FactGrid matched |
| `rejected — no match found` | Found a candidate but it was the wrong place |

---

## Column I — your judgment

| Value | Meaning |
|-------|---------|
| `auto` | I'm confident — no action needed unless something looks off |
| `Y` | You've reviewed it and are happy with column F |
| *(blank)* | Needs your attention |

**Please note**: If you correct column F, please also mark column I as `Y`.
If I run the script again, we might lose your correction.
For every row you touch: fix column F if needed, then mark `Y` in column I.

If you can't find the right item, leave column F empty and mark `Y` — that
tells me you've seen it and it needs further investigation. We might beam
those places up from wikidata.

---

## Compound place strings

Some original strings name two or more cities — e.g. "Como - Pavia". I've
split these into one row per city, so that item now appears as two rows, each
of which will generate a separate P241 statement. Where a compound string
already had a value in column F from your original work, I've preserved it
as-is.

---

## False positives

The matching process searches FactGrid by string, which means it can find the
right name but the wrong place. All known examples were correctly flagged
`stripped qualifier — VERIFY`, but they show why those rows need a look:

- **"Burlington, Vermont"** matched Burlington in Iowa
- **"Durham, NC"** matched County Durham, England
- **"Eugene, OR"** matched Eugene as a given name

I have no known silent false positives among `auto` rows, but can't guarantee
there aren't any — so if something catches your eye there, please do correct it.

---

## Updates and iteration

I can do another iteration of this script, maybe if I learn better ways to
do this, maybe if new objects were added to FG. Rows marked `Y` won't be touched.
