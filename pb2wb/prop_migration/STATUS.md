# P721 migration — remaining tasks

Living document. Update the status tables by hand when something changes; refresh
the numbers with `python prop_migration/task_status.py` (local only, no FactGrid
requests). Last edited: 2026-10-30.

## Usages remaining by group

<!-- usage-table -->
| Group | | Usages left | % of original | Cumulative done |
|---|---|---:|---:|---:|
| *Done* | | 111,396 | 84.2% | 84.2% |
| A8 | Foliation → P1243 | 0 | 0.0% | 84.2% |
| A8b | Physical descriptions → P1243 | 2 | 0.0% | 84.2% |
| A8c | Physical notes with a colon → P1243 | 4 | 0.0% | 84.2% |
| A6 | Pipeline-approved, awaiting Charles | 17 | 0.0% | 84.2% |
| A3 | Catalogue + evidence combos | 94 | 0.1% | 84.3% |
| A2 | Held: locator mismatch, DHEE vol. | 43 | 0.0% | 84.3% |
| held | Held bases (B2 works-vs-people, …) | 44 | 0.0% | 84.4% |
| A4/A5/A10 | Vetted, other blockers | 364 | 0.3% | 84.7% |
| A9 | Compounds (X / Y) | 241 | 0.2% | 84.8% |
| A7 | Long tail, no match | 20,054 | 15.2% | 100.0% |

_Generated 2026-10-30 by `task_status.py` from `P721-live.2026-10-29.tsv` (taken 2026-10-29T14:20 UTC) minus conversions logged since. Groups are assigned by list membership and keywords, so small-group boundaries are approximate._
<!-- /usage-table -->

## A. Forward conversion (P721 still in FactGrid)

| # | Group | Status | Waiting on |
|---|---|---|---|
| A6 | Pipeline-approved (Arteaga ~730 — Charles 10-29: vol./page, done 10-30, `plan_arteaga_20261030.tsv`, 728 usages; small ones left) | Max decided 10-29: BNE Cat. & Faulhaber (as person) → P129 + P702 evidence; Martz, Wikidata → convert. Running on the box (`plan_pipeline_exec_20261029.tsv`, 31 bases, ~245 usages). Rest goes to Charles (`email_to_charles_batch_20261029.txt`, `charles_questions_20261029.xlsx`). 3 targets point to places. | Charles: small items (email item 1) |
| A7 | Long tail, no match | PhiloBiblon + P73 note proposal drafted (`email_long_tail_draft.txt`), not sent. Do after A6. | Max: send to Olaf/Charles |
| A3 | Catalogue + evidence combos | Kind 3 done as A8c; kinds 1+2 and A3b done 10-29 (see Done). Left: catalogue picks needing a call (28 usages, `a3_catalogue_picks.tsv` status=check), no-hit prefixes (22, status=hold; Charles item 3), 28 author-year references, 9 skipped, 7 long physical notes (`a8d_excluded.tsv`). | Max: the 'check' picks; Charles: email item 3 |
| A2 | Vetted, with a locator — held remainder | 28 locator mismatches (`exclude_locator_mismatch.tsv`), 6 "DHEE I:nnn" volume-style bases. | Charles |
| A4 | Shelfmark locators and typos | Which property to use. | Max/Olaf |
| A5 | Vetted, but QID blank or malformed | | Charles |
| A9 | Compounds (X / Y) | Manual handling; held. | Charles |
| A10 | New strings since June | Triage not started. | Claude |
| A8 | "* Qualifier" = "?" (a different property) → P155 | Needs a count. | Claude: count query (ask Max first) |

### Done
| # | Group | Result |
|---|---|---|
| A1 | Vetted, no locator | Done 2026-10-27. |
| A2 | Vetted, with a locator | Non-DHEE 1,087 (10-27); DHEE 3,174 (10-28); leftovers 26 (10-28). |
| A8 | fichero; ?/[?] → P155 | 550; 157 (10-27/28). |
| A8 | Foliation → P1243 (`a8_foliation.tsv`) | 3,321 swapped 2026-10-28, language per item: 3,319 ca, 2 es. |
| A8b | Physical descriptions → P1243 (`a8b_physical.tsv`) | 1,108 swapped 2026-10-29: 1,025 ca, 77 es, 6 pt. |
| A8d | Remaining A3 physical notes → P1243 (`a8d_physical.tsv`) | 44 swapped 2026-10-30: 40 ca, 2 es, 1 pt items. 7 over 400 chars set aside (`a8d_excluded.tsv`). |
| A8c | Physical notes misfiled under A3 → P1243 (`a8c_physical.tsv`) | 397 swapped 2026-10-29: 377 ca, 19 es. |
| A3 (kinds 1+2) | Catalogue + evidence (`plan_a3_20261029.tsv`) | 436 converted 2026-10-29: P129 catalogue + P702 evidence, description → P1243. 0 errors, 357 spot-checks OK. |
| A3b | Catalogue QID search picks (`plan_a3b_20261029.tsv`) | 82 converted 2026-10-29 (68 bases), 0 errors, 77 spot-checks OK. |
| A6 (part) | Pipeline-approved: BNE Cat., Faulhaber, Martz, Wikidata, ex-libris ms., Dutton, Cronología, small catalogues | 379 converted 2026-10-29 (pipeline_exec, exlibris_ms, pipeline_exec2). |

## B. Fixes to references already written

| # | Group | Status | Waiting on |
|---|---|---|---|
| B5 | princeps: vetting sheet still has Q99745 on the 3 Illuminati rows (FactGrid has Q196098) | Fix in the sheet at the next sheet update. | Max |
| B8 | Items blocked by broken sitelinks (11) | Every write fails while the item has a stale wikidatawiki sitelink. Added 10-29: Q1079353 (sitelink Q108451548, now a redirect to Q16573599 on Wikidata). | Max: email Olaf |
| B3 | QIDs cleared by Charles | Replace or remove? | Charles |
| B4 | Wrong-kind targets not yet flagged | | Charles |
| B6 | Compounds converted with only one of their sources — parts with no QID (77) | Long tail. | — |
| B9 | Malformed QIDs in the sheet (460 rows) | Not started. | Claude |

### Done
| # | Group | Result |
|---|---|---|
| B1 | Re-pointed to an existing item | 526 corrected 2026-10-23. Leftovers checked 10-30 (70 stmts): none to apply — evidence words (P702), rejected targets, duplicate Dutton, cosmetic "f." locators, FactGrid better than sheet. Only open: Cronología 565 (sheet 623?) → Charles email item 1. |
| B2b | Held bases Charles vetted to a person (`plan_b2_held_20261029.tsv`, 38 bases) | 960 converted: 60 on 10-29 (stopped at 9 pm ET, FactGrid write 504s), 900 on 10-30 rerun. Timed-out items had saved; no duplicate refs. 2 spot-check read errors (Q1038744, Q1056023) checked OK by hand. |
| B2a | Re-pointed by Charles to new items (`correction_plan.b2_new_item.tsv`) | 186 corrected 2026-10-29; 1 already; 5 missing (Q1077042 ×2 fixed by Charles to Boynton (2011) in June; 3 statements gone). |
| B5 | Evidence words P129 → P702 (Bookplate, Colophon, …) | 375 moved 2026-10-28. 5 not found: changed by hand on FactGrid (3 → Real Biblioteca bindings DB Q1072164, 2 statements deleted). |
| B5 | princeps (563 statements) | Kept as P129 = First publication (Q196098). Charles 10-27: princeps = "information taken from the first edition"; 10-29 "Exactly right" on the statement list. |
| B6 | Compounds: add references for the other sources (`correction_plan.b6_add.tsv`) | 316 added 2026-10-30 on 311 statements; 6 missing (statements gone); read-back 36 OK. |
| B4 (part) | "MS"/"MSS" → P702 Based on: Manuscript (`move_plan_ms_p702.tsv`) | 22 moved 2026-10-30. |
| A7 (part) | Top strings with a settled or single-match QID (`plan_a7_ready_20261030.tsv`) | 504 converted 2026-10-30 (34 bases), 0 errors, 102 spot-checks OK. Rest of the top 285: `a7_top_picks.tsv` (check 117 / none 103) → Charles sheet or long tail. |
| A6 Arteaga | vol./page per Charles (`plan_arteaga_20261030.tsv`) | 728 converted 2026-10-30. |
| B7 | Missing locators | DHEE pages added to 87 statements 2026-10-28; rest overlaps A3. |

## C. Infrastructure

| # | Item | Status |
|---|---|---|
| C2 | Safe sheet push | Open. Don't push p721. |
| C3 | Example-item and status columns in the sheet | Built; on hold until Charles answers. |
| C5 | job_queue output unbuffered | Open (worker now started with `python -u`). |
| C1, C4 | Straggler sweep; re-login on expiry | Done. |

## Open questions for other people

- **Olaf**: nightly write outage still exists, apparently ~1:00 am Berlin time (2026-06-08 7:00–7:44 pm EDT; 2026-10-29 504s on writes from 8:01 pm EDT, intermittent until at least 9 pm; reads fine). What is it, how long? Queue window now 00:50–01:50 Berlin. B8 broken sitelinks. A7 proposal.
- **Charles** (email draft, 3 items): A6 small items; B3 cleared QIDs; A3 "which work?". Also A2/A5/A9 manual items.
