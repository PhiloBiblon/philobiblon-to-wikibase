# Source-Citation Mapping (P721→P129) — Notes for Charles

I have updated ["Reference sources"](https://docs.google.com/spreadsheets/d/1Nm5js5zSK5dlLz9aMeFK03s1WnfH8T-zq3sOWEn_HEw/edit?gid=467222215#gid=467222215) sheet I sent you in June
2025. I've incorporated your earlier work and rebuilt the sheet with a richer
structure. The core columns you already know (`freq`, `basis`, `key`, `loc`)
are still there with the same meaning, and there are several new columns
described below.

The sheet has about 17,000 rows covering 132,000 individual bases. I've sorted in by Column A
(frequency) but you can sort it as you like. I'm asking you to vet the "qid" column, which I have 
filled in as best I could, with the aid of my friend the AI. 

---

## Columns of interest

| Column | Name | Contents |
|--------|------|----------|
| A | freq | How many times this basis string appears — higher = more important |
| B | basis | The original P721 string — please don't edit this |
| C | key | The searchable part I extracted (e.g. "Beltrán 1997" from "Beltrán 1997:60") |
| D | match_type | How I found the match — set automatically, see below |
| E | qid | FactGrid item QID — **the most important thing to review** |
| F | label | The FG label of that item |
| G | vetted | Your judgment — please populate this |
| H | loc_type | Type of locator: page, folio, footnote, volume, or blank — new, see below |
| I | loc | Locator value (e.g. "60", "93v") — same as the old column D |

---

## The most important thing: vetting the QIDs

Column E is what matters most. Each QID identifies the FactGrid item that will
be used as the structured reference when we do the actual data conversion. A
wrong QID here means wrong data in FactGrid, so I'd like you to check as many
as you can — especially the high-frequency rows.

For every row where you're satisfied with the QID in column E, please mark `Y`
in column G. That shows me which ones you have approved and which ones remain.

**Important**: if you correct any cell in a row, please also mark `Y` in
column G — otherwise the next run of the script may overwrite your correction.


---

## The new loc_type column (H)

The June sheet had a single `loc` column for locators like page numbers,
folio references, and volume numbers. I've now split this into two columns:
`loc_type` (H) and `loc` (I). The reason is that different locator types may map
to different FactGrid properties when we do the conversion — a page number
might use a different property than a folio reference or a footnote number. Column
H records which type it is so the script knows which property to use.

If I've got the locator type or value wrong, feel free to correct either column
and mark `Y` in column G.

---

## Column D — how I found the match

| Value | Meaning |
|-------|---------|
| `vetted` | Carried forward from your earlier work — already locked |
| `known` | From a curated list I maintain — high confidence |
| `api_label` | Exact FactGrid label match — high confidence |
| `api_alias` | Exact FactGrid alias match — high confidence |
| `api_fuzzy` | FactGrid returned a hit but the label differs from my search key — worth checking |
| `none` | Nothing found — if you recognize it, please add the QID in column E |
| `excluded` | Not a bibliographic reference (e.g. "fol. mod.", "?") — no action needed |
| `shelfmark` | Library call number — nothing useful to do with these for now |
| `llm_pending` | Couldn't parse automatically — only 2 rows, I'll handle these manually |

I believe I've initialized column D to "vetted" for all the rows that you looked 
at in the earlier version. 

---

## Where to focus

The `api_fuzzy` rows are the ones most in need of attention — about 2,900 rows
covering nearly 37,000 basis assertions. The match may be correct or it may be the wrong
work by the same author or the wrong type (a person or place where it should be a work -- although I've  tried to avoid that). Sorting by column A (frequency) and working from the
top down makes sense, since the high-frequency ones have the most impact.

We don't need to resolve every row before converting basis assertions to references. We could resolve 21,000 of the 132,000 just by converting the "Faulhaber" bases. In more detail:

| Top N strings | Usages covered | % of 132,259 total |
|---|---:|---:|
| 1 | 21,531 | 16% |
| 5 | 40,847 | 31% |
| 10 | 52,847 | 40% |
| 20 | 60,205 | 46% |
| 50 | 70,476 | 53% |
| 100 | 78,704 | 60% |
| 200 | 86,317 | 65% |
| 500 | 96,996 | 73% |
| 1,000 | 104,421 | 79% |

So the remaining 16,000+ rare strings account for only 21% of the database.

The `known`, `api_label`, and `api_alias` rows are high confidence — no need
to review them systematically, though if something catches your eye please do
correct it.

The `none` rows are numerous (~11,000) but most have low frequency. I wouldn't
worry about working through them systematically — just add a QID in column E
if you happen to recognize something, and mark `Y`.

---

## Iterating

We'll likely go through several rounds of this. Two things might prompt a new
run of the script:

- You spot something that looks systematically wrong — a bug in my matching
  logic, or a pattern I'm handling badly. If you let me know, I can fix it
  and rerun, which may improve a whole class of rows at once.
- Rows that currently show `none` may get matched in a future run, either
  because new items have been added to FactGrid or because I've improved the
  matching rules.

In either case, rows you've marked `Y` will always be preserved — they won't
be touched by subsequent runs.
