# Vetting the Place-of-Publication Mapping

## What this spreadsheet is

Each row represents one PhiloBiblon item that has a place-of-publication string
(column C).  We have tried to match each string to the corresponding place item
in FactGrid (column F, **P241 Qid**).  Your job is to check our work and approve,
correct, or flag each assignment.

---

## Columns you care about

| Column | Name | What it contains |
|--------|------|-----------------|
| C | _Place_of_publication | The place string as it appears in the database |
| F | P241 Qid | A link to the FactGrid place item we matched (click to verify) |
| G | P241_values | The plain-text label of that item |
| H | auto_match | A note explaining how confident we are (see below) |
| I | vetted | **This is where you record your review** |

---

## The `auto_match` column — what the notes mean

| Note | What it means |
|------|--------------|
| *(blank)* | High confidence — matched exactly on the item's label or a known alias |
| `stripped qualifier — VERIFY` | We stripped a qualifier like ", PA" or "[Mass]" to find the match — please confirm the link is the right city |
| `VERIFY` | Lower-confidence match — the name differs slightly from what we searched |
| `compound — split (City)` | This string names two cities; this row covers one of them |
| `compound — needs split` | Multi-city string we couldn't split automatically — needs manual attention |
| `no match found` | Nothing in FactGrid matched — the place may not have an item yet |
| `rejected — no match found` | We found a candidate but it was geographically wrong (e.g. wrong US state) |

---

## The `vetted` column — how to record your review

| Value | Meaning |
|-------|---------|
| `auto` | We pre-approved this as high confidence — you don't need to check it, but you can |
| `Y` | **You** have personally reviewed this row and are happy with column F |
| *(blank)* | Still needs your attention |

---

## What to do, row by row

### Rows where `vetted` = `auto`
We are confident in these.  You don't need to do anything.  If one catches
your eye and looks wrong, correct column F and change `auto` to `Y`.

### Rows where `vetted` is blank
These need your attention.  For each one:

1. **Click the link in column F** to open the FactGrid item.
2. Check that it is the right place (pay attention to country/state in the
   item description).
3. If it looks correct: type **Y** in the `vetted` column (column I).
4. If it is wrong: replace the link in column F with the correct FactGrid
   item, then type **Y** in `vetted`.  If you can't find the right item,
   clear column F and leave `vetted` blank — we will investigate.
5. If the place name in column C is misspelled or garbled: correct it in
   column C as well.  This helps us if we need to re-run the matching.

### "no match found" rows
The place string did not match anything in FactGrid.  Options:
- If you know the correct FactGrid item, paste its link into column F and
  type **Y** in `vetted`.
- If the place doesn't have a FactGrid item yet, leave column F blank and
  type **Y** in `vetted` to indicate you've seen it.
- If the string in column C is so garbled that you're not sure what place
  is meant, leave both blank and add a note in column H.

### "compound" rows
These strings contain two or more cities (e.g. "London - New York").  We
have tried to split them into one row per city.  Check each split row as
you would a normal row.  If the split is wrong or a city is missing, let
Max know.

---

## Asking for a fresh run

You don't need to finish every row before asking for a new round of
predictions.  At any point you can send the sheet back and we will:

1. Preserve all rows where `vetted` = `Y` or `auto` (we won't touch those).
2. Re-run matching on everything else, picking up any corrections you've
   made to column C.
3. Return an updated sheet.

---

## Summary checklist

- [ ] Work through rows where `vetted` is blank
- [ ] For each: click the column F link, confirm or correct, type Y in column I
- [ ] Correct any misspellings in column C as you go
- [ ] Send the sheet back to Max when you're ready for another round (or when done)
