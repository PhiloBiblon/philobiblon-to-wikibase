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
