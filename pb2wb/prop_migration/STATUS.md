# P721 migration — remaining tasks

Living document. Update the status tables by hand when something changes; refresh
the numbers with `python prop_migration/task_status.py` (local only, no FactGrid
requests). Last edited: 2026-11-01 (midday).

## Usages remaining by group

<!-- usage-table -->
| Group | | Usages left | % of original | Cumulative done |
|---|---|---:|---:|---:|
| *Done* | | 112,094 | 84.8% | 84.8% |
| A8 | Foliation → P1243 | 0 | 0.0% | 84.8% |
| A8b | Physical descriptions → P1243 | 2 | 0.0% | 84.8% |
| A8c | Physical notes with a colon → P1243 | 4 | 0.0% | 84.8% |
| A6 | Pipeline-approved, awaiting Charles | 17 | 0.0% | 84.8% |
| A3 | Catalogue + evidence combos | 94 | 0.1% | 84.8% |
| A2 | Held: locator mismatch, DHEE vol. | 43 | 0.0% | 84.9% |
| held | Held bases (B2 works-vs-people, …) | 44 | 0.0% | 84.9% |
| A4/A5/A10 | Vetted, other blockers | 140 | 0.1% | 85.0% |
| A9 | Compounds (X / Y) | 150 | 0.1% | 85.1% |
| A7 | Long tail, no match | 19,671 | 14.9% | 100.0% |

_Generated 2026-11-01 by `task_status.py` from `P721-live.2026-10-29.tsv` (taken 2026-10-29T14:20 UTC) minus conversions logged since. Groups are assigned by list membership and keywords, so small-group boundaries are approximate._
<!-- /usage-table -->

## Plan (Max, updated 2026-11-01)

1. **Clean up what Max can do alone** — only work worth ≥100 usages, or small items that
   are completely ready to go. Done through 11-01 (A7 top strings and folios, A9, A4/A5 part,
   evidence-item fix); what's left is punted.
2. **Freeze the old vetting sheet** — Charles hasn't edited it since 10-20 (pull of 10-31 was
   identical). Make it read-only (Max: Google Sheets sharing/protection). The regenerated
   sheet (same columns, ~10,000 open strings, status/example columns, seeded into a new Google
   Sheet) is on hold — the long-tail plan would replace most of what it would ask.
3. **Tell Charles the long-tail plan is recommended next** (`email_to_charles_long_tail_draft.txt`,
   numbers to refresh, plus a line about the read-only sheet); then Olaf
   (`email_long_tail_draft.txt` as the starting point).

## Long-tail plan (proposed, not agreed)

For strings with no FactGrid item, replace the P721 qualifier with a reference that keeps
the text: P129 According to = PhiloBiblon, P73 Note = the original string. Reversible: when
a string is identified later, the correction script swaps PhiloBiblon for the real work.
- Would cover: A7 (~19,700), B4 wrong-kind references (~1,250 statements, minus the
  exceptions below), B3 cleared QIDs (~300), B6 parts with no QID (77).
- Not for non-sources: notes like "muerte" (67+18+…) need their own treatment first.
- Open for Olaf: P73 inside a reference OK? One PhiloBiblon item, or BETA/BITECA/BITAGAP?

## A. Forward conversion (P721 still in FactGrid)

| # | Group | Status | Waiting on |
|---|---|---|---|
| A7 | Long tail, no match (~19,700) | Top 285 strings searched 10-30 (`a7_top_picks.tsv`): 504 converted; left: 117 "check" (2,007 usages; only "Andrés" 157 and "Avenoza 2001" 105 reach 100) and 103 no hit (1,886). Non-source notes ("muerte", "muerte Santillana", "fechas del original y del MS", "lletra", "sello", "fot. parc.") need a modelling decision. Rest → long-tail plan. | Max: Andrés, Avenoza 2001; Charles sheet; long-tail plan |
| A6 | Pipeline-approved, small items (17) | Places (DMA, Santa Cruz, Vila), "renunció: DHEE" ×4, Castro ×2, BNM 11439 y 12580, Andrés xxvi, DHEE 311, 557. | Charles (email item 1) |
| A3 | Catalogue + evidence leftovers (94) | 28 'check' picks (`a3_catalogue_picks.tsv`), 22 no hit, 28 author-year references, 9 skipped, 7 long notes (`a8d_excluded.tsv`). Punted (<100). | Charles sheet / long tail |
| A9 | Compounds (X / Y) — parts with no QID (~150) | Waits for the long-tail plan (the note would keep the whole string). | — |
| A4 | Shelfmark locators (~53: Colombina, B Catalunya, Ajuda…) | Which property to use. Punted (<100). | Max/Olaf |
| A2 | Vetted, with a locator — held remainder (43) | 28 locator mismatches (`exclude_locator_mismatch.tsv`), 6 "DHEE I:nnn" volume-style bases. Punted. | Charles |
| A5 | Vetted, but QID blank or malformed (~60) | Y with no QID (Blüher 142, Leitura nova 61, Colón Abecedarium…), "vetted" as QID (Hobson 1976, Díez Garretas 1997), Brown/Princeton URLs. Punted. | Charles |
| A10 | New strings since June | Triage not started. | Claude |
| A8 | "* Qualifier" = "?" (a different property) → P155 | Needs a count. | Claude: count query (ask Max first) |

### Done
| # | Group | Result |
|---|---|---|
| A1 | Vetted, no locator | Done 2026-10-27. |
| A2 | Vetted, with a locator | Non-DHEE 1,087 (10-27); DHEE 3,174 (10-28); leftovers 26 (10-28). |
| A3 (kinds 1+2) | Catalogue + evidence (`plan_a3_20261029.tsv`) | 436 converted 2026-10-29: P129 catalogue + P702 evidence, description → P1243. 0 errors, 357 spot-checks OK. |
| A3b | Catalogue QID search picks (`plan_a3b_20261029.tsv`) | 82 converted 2026-10-29 (68 bases), 0 errors, 77 spot-checks OK. |
| A6 (part) | Pipeline-approved: BNE Cat., Faulhaber, Martz, Wikidata, ex-libris ms., Dutton, Cronología, small catalogues | 379 converted 2026-10-29 (pipeline_exec, exlibris_ms, pipeline_exec2). |
| A6 Arteaga | vol./page per Charles 10-29 (`plan_arteaga_20261030.tsv`) | 728 converted 2026-10-30. |
| A7 (part) | Top strings with a settled or single-match QID (`plan_a7_ready_20261030.tsv`) | 504 converted 2026-10-30 (34 bases), 0 errors, 102 spot-checks OK. |
| A7 (part) | Folio references and folio-led notes → P1243 (`a7_folio_notes.tsv`) | 383 swapped 2026-10-30 (232 bases): 178 es, 98 ca, 10 pt items. 4 naming a source left in A7. |
| A9 (part) | Compounds whose parts all have QIDs (`plan_a9_20261101.tsv`, then `correction_plan.a9_add.tsv`) | 91 converted 2026-11-01 with the first part's reference (69 bases; 85 spot-checks OK). Second parts: 91 references added 2026-11-01 (read-back 12 OK). Left out: "Zarco / Cuenca 2017" (bad match), "Catalogus 1682 / Högberg 1919" (year given as page). |
| A4/A5 (part) | Pathfinder → OskiCat Q1071201 (Berkeley's catalogue; statements are "Berkeley holds a copy"), BNE MSS/2420 without its redundant locator, annotation notes → P1243 (`plan_a4_ready_20261101.tsv`) | 224 converted 2026-11-01 (46 bases). |
| A8 | fichero; ?/[?] → P155 | 550; 157 (10-27/28). |
| A8 | Foliation → P1243 (`a8_foliation.tsv`) | 3,321 swapped 2026-10-28, language per item: 3,319 ca, 2 es. |
| A8b | Physical descriptions → P1243 (`a8b_physical.tsv`) | 1,108 swapped 2026-10-29: 1,025 ca, 77 es, 6 pt. |
| A8c | Physical notes misfiled under A3 → P1243 (`a8c_physical.tsv`) | 397 swapped 2026-10-29: 377 ca, 19 es. |
| A8d | Remaining A3 physical notes → P1243 (`a8d_physical.tsv`) | 44 swapped 2026-10-30: 40 ca, 2 es, 1 pt items. 7 over 400 chars set aside (`a8d_excluded.tsv`). |

## B. Fixes to references already written

| # | Group | Status | Waiting on |
|---|---|---|---|
| B4 | Wrong-kind targets (`b4_wrong_kind.tsv`: 1,247 statements, 276 targets) | Mostly surnames → towns (~830). Charles marked 695 of them Y without noticing the target type. Exceptions: "Compilación A" → Voragine translation (89) is probably correct; "Santander BMyP 169 (8)" → Penna (73) needs the MS item; "1r" → "1st" (14) belongs in P1243. Surnames with ≥10 statements (~20 targets, ~350) → Charles sheet; rest → long-tail plan. | Charles sheet / long tail |
| B3 | QIDs cleared by Charles (24 bases / 233) | Replace or remove? Fits the long-tail plan. Almena = Valladolid catalogue (asked). | Charles (email item 2) / long tail |
| B8 | Items blocked by a broken link (`b8_blocked_items.tsv`) | Checked 2026-11-01 (sitelinks + Commons files of the 15 items that ever failed): **2 still blocked** — Q1307780 (image P189 → deleted Commons file "Afonso I of Portugal (12th century).png") and Q1079353 (wikidatawiki → Q108451548, now a redirect; its 4 "Wikidata" usages wait on this). The other 13 have working links now; their leftovers can be retried. | Max: email Olaf (2 items) |
| B5 | princeps: vetting sheet still has Q99745 on the 3 Illuminati rows (FactGrid has Q196098) | Fix in the sheet at the next sheet update. | Max |
| B6 | Compound parts with no QID (77) | Long-tail plan. | — |
| B9 | Malformed QIDs in the sheet (37 rows) | 25 mechanical ("Item:Q…", URLs) but only 11 usages; one QID cut off ("Q1070"). Punted. | — |

### Done
| # | Group | Result |
|---|---|---|
| B1 | Re-pointed to an existing item | 526 corrected 2026-10-23. Leftovers checked 10-30 (70 stmts): none to apply — evidence words (P702), rejected targets, duplicate Dutton, cosmetic "f." locators, FactGrid better than sheet. Only open: Cronología 565 (sheet 623?) → Charles email item 1. |
| B2a | Re-pointed by Charles to new items (`correction_plan.b2_new_item.tsv`) | 186 corrected 2026-10-29; 1 already; 5 missing (Q1077042 ×2 fixed by Charles to Boynton (2011) in June; 3 statements gone). |
| B2b | Held bases Charles vetted to a person (`plan_b2_held_20261029.tsv`, 38 bases) | 960 converted: 60 on 10-29 (stopped at 9 pm ET, FactGrid write 504s), 900 on 10-30 rerun. Timed-out items had saved; no duplicate refs. 2 spot-check read errors (Q1038744, Q1056023) checked OK by hand. |
| B4 (part) | "MS"/"MSS" → P702 Based on: Manuscript (`move_plan_ms_p702.tsv`) | 22 moved 2026-10-30. |
| B5 | Evidence words P129 → P702 (Bookplate, Colophon, …) | 375 moved 2026-10-28. 5 not found: changed by hand on FactGrid (3 → Real Biblioteca bindings DB Q1072164, 2 statements deleted). |
| B5 | princeps (563 statements) | Kept as P129 = First publication (Q196098). Charles 10-27: princeps = "information taken from the first edition"; 10-29 "Exactly right" on the statement list. |
| B6 | Compounds: add references for the other sources (`correction_plan.b6_add.tsv`) | 316 added 2026-10-30 on 311 statements; 6 missing (statements gone); read-back 36 OK. |
| B5 fix | Evidence items: Guarda the town (Q358912) → Guarda / fly leaf (Q395036); Escudo the currency (Q960940) → Escudo de armas (Q11233) (`correction_plan.evidence_swap.tsv`) | 44 corrected 2026-11-01 (14, then 30 after fixing the skip key). Charles had the right items in the sheet; dismissed by mistake in the 10-30 B1 leftover check. Types of all 54 targets chosen since 10-23 checked (`new_target_types.tsv`): fine. |
| B7 | Missing locators | DHEE pages added to 87 statements 2026-10-28; rest overlaps A3. |

## C. Infrastructure

| # | Item | Status |
|---|---|---|
| C2 | Safe sheet push | Open. Don't push p721. |
| C3 | Example-item and status columns in the sheet | Built; on hold until Charles answers. |
| C5 | job_queue output unbuffered | Open (worker now started with `python -u`). |
| C6 | Maintenance window | Done 10-30: defined in Berlin time, 00:50–01:50 (commit 5040f01). Only blocks job *starts*. |
| C1, C4 | Straggler sweep; re-login on expiry | Done. |

## Open questions for other people

- **Charles**:
  - Batch email (`email_to_charles_batch_20261029.txt`, 3 items): A6 small items incl. Cronología 565; B3 cleared QIDs; A3 "which work?". May be folded into the new spreadsheet.
  - Long-tail plan (`email_to_charles_long_tail_draft.txt`), first.
- **Olaf**: nightly write outage still exists, apparently ~1:00 am Berlin time (2026-06-08 7:00–7:44 pm EDT; 2026-10-29 504s on writes from 8:01 pm EDT, intermittent until at least 9 pm; reads fine). What is it, how long? B8 broken sitelinks. Duplicate Dutton items (Q1070186 / Q1078975). Long-tail plan once Charles agrees.
