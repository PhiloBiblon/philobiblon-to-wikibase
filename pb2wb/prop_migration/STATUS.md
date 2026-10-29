# P721 migration — remaining tasks

Living document. Update the status tables by hand when something changes; refresh
the numbers with `python prop_migration/task_status.py` (local only, no FactGrid
requests). Last edited: 2026-10-29.

## Usages remaining by group

<!-- usage-table -->
| Group | | Usages left | % of original | Cumulative done |
|---|---|---:|---:|---:|
| *Done* | | 109,160 | 82.5% | 82.5% |
| A8 | Foliation → P1243 | 0 | 0.0% | 82.5% |
| A8b | Physical descriptions → P1243 | 2 | 0.0% | 82.5% |
| A8c | Physical notes with a colon → P1243 | 4 | 0.0% | 82.5% |
| A6 | Pipeline-approved, awaiting Charles | 745 | 0.6% | 83.1% |
| A3 | Catalogue + evidence combos | 138 | 0.1% | 83.2% |
| A2 | Held: locator mismatch, DHEE vol. | 43 | 0.0% | 83.2% |
| held | Held bases (B2 works-vs-people, …) | 1,003 | 0.8% | 84.0% |
| A4/A5/A10 | Vetted, other blockers | 364 | 0.3% | 84.3% |
| A9 | Compounds (X / Y) | 241 | 0.2% | 84.5% |
| A7 | Long tail, no match | 20,559 | 15.5% | 100.0% |

_Generated 2026-10-29 by `task_status.py` from `P721-live.2026-10-29.tsv` (taken 2026-10-29T14:20 UTC) minus conversions logged since. Groups are assigned by list membership and keywords, so small-group boundaries are approximate._
<!-- /usage-table -->

## A. Forward conversion (P721 still in FactGrid)

| # | Group | Status | Waiting on |
|---|---|---|---|
| A6 | Pipeline-approved (Arteaga ~730, Dutton 77, Cronología 47, small ones) | Max decided 10-29: BNE Cat. & Faulhaber (as person) → P129 + P702 evidence; Martz, Wikidata → convert. Running on the box (`plan_pipeline_exec_20261029.tsv`, 31 bases, ~245 usages). Rest goes to Charles (`email_to_charles_batch_20261029.txt`, `charles_questions_20261029.xlsx`). 3 targets point to places. | Charles: Arteaga, Dutton, Cronología, the rest |
| A7 | Long tail, no match | PhiloBiblon + P73 note proposal drafted (`email_long_tail_draft.txt`), not sent. Do after A6. | Max: send to Olaf/Charles |
| A3 | Catalogue + evidence combos | Kind 3 done as A8c; kinds 1+2 and A3b done 10-29 (see Done). Left: catalogue picks needing a call (28 usages, `a3_catalogue_picks.tsv` status=check) and no-hit prefixes (22, status=hold; Charles item 6); ~20 author-year references; 42 usages of physical notes (A8c-style); 29 references (kind 4). | Max: the 'check' picks; Charles: item 6 |
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
| A8c | Physical notes misfiled under A3 → P1243 (`a8c_physical.tsv`) | 397 swapped 2026-10-29: 377 ca, 19 es. |
| A3 (kinds 1+2) | Catalogue + evidence (`plan_a3_20261029.tsv`) | 436 converted 2026-10-29: P129 catalogue + P702 evidence, description → P1243. 0 errors, 357 spot-checks OK. |
| A3b | Catalogue QID search picks (`plan_a3b_20261029.tsv`) | 82 converted 2026-10-29 (68 bases), 0 errors, 77 spot-checks OK. |
| A6 (part) | Pipeline-approved: BNE Cat., Faulhaber, Martz, Wikidata, ex-libris ms., Dutton, Cronología, small catalogues | 379 converted 2026-10-29 (pipeline_exec, exlibris_ms, pipeline_exec2). |

## B. Fixes to references already written

| # | Group | Status | Waiting on |
|---|---|---|---|
| B5 | princeps (~560 statements) | List for Charles built (`princeps_statements.xlsx`). 3 wrong Illuminati targets fixed 10-28; vetting sheet still has Q99745 on those 3 rows. | Max: send list; Charles: modelling |
| B2 | Re-pointed to new items, often persons (192 statements) | Draft question exists. | Charles: works vs people |
| B8 | Items blocked by broken sitelinks (11) | Every write fails while the item has a stale wikidatawiki sitelink. Added 10-29: Q1079353 (sitelink Q108451548, now a redirect to Q16573599 on Wikidata). | Max: email Olaf |
| B3 | QIDs cleared by Charles | Replace or remove? | Charles |
| B4 | Wrong-kind targets not yet flagged | | Charles |
| B6 | Compounds converted with only the first source | | Charles |
| B9 | Malformed QIDs in the sheet (460 rows) | Not started. | Claude |

### Done
| # | Group | Result |
|---|---|---|
| B1 | Re-pointed to an existing item | 526 corrected 2026-10-23. |
| B5 | Evidence words P129 → P702 (Bookplate, Colophon, …) | 375 moved 2026-10-28. 5 not found: changed by hand on FactGrid (3 → Real Biblioteca bindings DB Q1072164, 2 statements deleted). |
| B7 | Missing locators | DHEE pages added to 87 statements 2026-10-28; rest overlaps A3. |

## C. Infrastructure

| # | Item | Status |
|---|---|---|
| C2 | Safe sheet push | Open. Don't push p721. |
| C3 | Example-item and status columns in the sheet | Built; on hold until Charles answers. |
| C5 | job_queue output unbuffered | Open (worker now started with `python -u`). |
| C1, C4 | Straggler sweep; re-login on expiry | Done. |

## Open questions for other people

- **Olaf**: does FactGrid's daily ~7 pm ET downtime still exist after the move? (Last seen 2026-06-08, 7:00–7:44 pm ET.) B8 broken sitelinks. A7 proposal.
- **Charles**: A6 Arteaga + approval; B2 works vs people; B5 princeps modelling; A2/A5/A9 manual items.
