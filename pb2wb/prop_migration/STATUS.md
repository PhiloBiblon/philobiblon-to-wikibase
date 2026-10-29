# P721 migration — remaining tasks

Living document. Update the status tables by hand when something changes; refresh
the numbers with `python prop_migration/task_status.py` (local only, no FactGrid
requests). Last edited: 2026-10-29.

## Usages remaining by group

<!-- usage-table -->
| Group | | Usages left | % of original | Cumulative done |
|---|---|---:|---:|---:|
| *Done* | | 107,863 | 81.6% | 81.6% |
| A8 | Foliation → P1243 | 0 | 0.0% | 81.6% |
| A8b | Physical descriptions → P1243 | 2 | 0.0% | 81.6% |
| A6 | Pipeline-approved, awaiting Charles | 1,126 | 0.9% | 82.4% |
| A3 | Catalogue + evidence combos | 1,059 | 0.8% | 83.2% |
| A2 | Held: locator mismatch, DHEE vol. | 43 | 0.0% | 83.2% |
| held | Held bases (B2 works-vs-people, …) | 1,003 | 0.8% | 84.0% |
| A4/A5/A10 | Vetted, other blockers | 364 | 0.3% | 84.3% |
| A9 | Compounds (X / Y) | 241 | 0.2% | 84.5% |
| A7 | Long tail, no match | 20,558 | 15.5% | 100.0% |

_Generated 2026-10-29 by `task_status.py` from `P721-live.2026-10-27.tsv` (taken 2026-10-27T12:29 UTC) minus conversions logged since. Groups are assigned by list membership and keywords, so small-group boundaries are approximate._
<!-- /usage-table -->

## A. Forward conversion (P721 still in FactGrid)

| # | Group | Status | Waiting on |
|---|---|---|---|
| A6 | Pipeline-approved (263 bases; Arteaga 754 usages) | Ready to run once approved. 4 wrong-kind targets (Dominica, Santa Cruz, Vila, Villalba) need fixing. | Charles: Arteaga = Q1069178? approve the rest |
| A7 | Long tail, no match | PhiloBiblon + P73 note proposal drafted (`email_long_tail_draft.txt`), not sent. Do after A6. | Max: send to Olaf/Charles |
| A3 | Catalogue + evidence combos ("BNE Cat.: sello", "IBIS: ex-libris") | Model decided: P129 catalogue + P702 evidence item. Needs a word → evidence-item mapping and a small tool change. Includes references set aside from A8b (`a8b_excluded.tsv`). | Claude: build mapping |
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

## B. Fixes to references already written

| # | Group | Status | Waiting on |
|---|---|---|---|
| B5 | princeps (~560 statements) | List for Charles built (`princeps_statements.xlsx`). 3 wrong Illuminati targets fixed 10-28; vetting sheet still has Q99745 on those 3 rows. | Max: send list; Charles: modelling |
| B2 | Re-pointed to new items, often persons (192 statements) | Draft question exists. | Charles: works vs people |
| B8 | Items blocked by broken sitelinks (10) | Someone with rights must clean them. | Max: email Olaf |
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
