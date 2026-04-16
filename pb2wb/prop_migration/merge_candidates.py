"""
merge_candidates.py — populate column F (P241 Qid) in the student sheet
from place_candidates.tsv, producing a TSV ready to upload to Google Sheets.

Reads:
  place_candidates.tsv          — per-string candidates from fill_gaps.py
  P1141-P241.tsv  — sheet (per-item rows)

Writes:
  sheet_updated.tsv — student sheet with P241 Qid and P241_values filled in
                      for matched strings, plus a new auto_match column.

Compound handling
-----------------
When fill_gaps.py was run with --llm, compound strings have a JSON 'parts'
column listing the resolved constituent cities.  For each compound row in the
student sheet, this script emits one output row per resolved part, each with
its own clickable P241 Qid.  Unresolved compound parts (no QID found) still
get a row so Charles can see what's missing.

Column F is written as a Google Sheets HYPERLINK formula so it is clickable:
  =HYPERLINK("https://database.factgrid.de/wiki/Item:Q81970","Q81970")

auto_match column values:
  blank                  — high confidence (api_label, api_alias, latin_lookup, sheet)
  VERIFY                 — corrections, fuzzy, or stripped match; Charles should confirm
  compound — split       — one of several cities from a compound string
  compound — needs split — compound with no LLM parts available
  no match found         — nothing in FactGrid; may need item creation
  rejected               — LLM verification found match geographically wrong

Existing P241 Qid values in the sheet are preserved as-is.

Usage (from pb2wb/):
    python prop_migration/merge_candidates.py
"""

import os
import sys
import re
import csv
import json
import argparse

dir_path = os.path.dirname(os.path.realpath(__file__))
parent_dir_path = os.path.dirname(dir_path)
sys.path.append(parent_dir_path)

from common.settings import BASE_IMPORT_OBJECTS

FG_WIKI_BASE = 'https://database.factgrid.de/wiki/Item:'

CANDIDATES_TSV = 'prop_migration/place_candidates.tsv'
SHEET_TSV      = 'prop_migration/P1141-P241.tsv'
OUT_TSV        = 'prop_migration/sheet_updated.tsv'

BARE_QID_RE = re.compile(r'^Q\d+$')


def qid_to_hyperlink(qid):
    return f'=HYPERLINK("{FG_WIKI_BASE}{qid}","{qid}")'


def hyperlink_if_qid(value):
    """Return a HYPERLINK formula if value is a bare QID, otherwise unchanged."""
    if BARE_QID_RE.match(value.strip()):
        return qid_to_hyperlink(value.strip())
    return value


def extract_qid(cell_value):
    """
    Extract a bare QID from any of these formats (tolerant):
      Q81970
      =HYPERLINK("https://.../Item:Q81970","Q81970")
      https://database.factgrid.de/wiki/Item:Q81970
    Returns '' if no QID found.
    """
    m = re.search(r'Q\d+', cell_value)
    return m.group(0) if m else ''


def auto_match_note(match_type):
    """Human-readable note for the auto_match column."""
    if match_type in ('sheet', 'api_label', 'api_alias', 'latin_lookup'):
        return ''
    if match_type == 'corrections':
        return 'VERIFY'
    if match_type in ('api_label_stripped', 'api_alias_stripped'):
        return 'stripped qualifier — VERIFY'
    if match_type in ('api_fuzzy', 'api_fuzzy_stripped'):
        return 'VERIFY'
    if match_type in ('api_label_retry', 'api_alias_retry'):
        return 'retry match — VERIFY'
    if match_type == 'rejected':
        return 'rejected — no match found'
    if match_type == 'compound':
        return 'compound — needs split'
    if match_type == 'none':
        return 'no match found'
    return ''


def vetted_value(match_type):
    """Initial value for the vetted column.
    High-confidence matches get 'auto' (trusted without manual review).
    Everything else is blank — Charles must review and type Y when satisfied.
    """
    if match_type in ('sheet', 'api_label', 'api_alias', 'latin_lookup'):
        return 'auto'
    return ''


def main():
    parser = argparse.ArgumentParser(
        description='Merge place candidates into student sheet')
    parser.add_argument('--candidates', default=CANDIDATES_TSV)
    parser.add_argument('--sheet',      default=SHEET_TSV)
    parser.add_argument('--out',        default=OUT_TSV)
    args = parser.parse_args()

    print(f'Reading candidates: {args.candidates}')
    # --- Load candidates: string → {qid, label, match_type, parts} ---
    candidates = {}
    with open(args.candidates, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            s = row['p1141_value'].strip()
            parts_json = row.get('parts', '').strip()
            try:
                parts = json.loads(parts_json) if parts_json else []
            except json.JSONDecodeError:
                parts = []
            candidates[s] = {
                'qid':        extract_qid(row['candidate_qid']),
                'label':      row['candidate_label'].strip(),
                'match_type': row['match_type'].strip(),
                'parts':      parts,   # list of {part, qid, label} for compounds
            }

    print(f'Reading sheet:      {args.sheet}')
    # --- Process student sheet ---
    out_rows = []
    filled = unchanged = skipped = 0

    with open(args.sheet, encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        in_fieldnames = reader.fieldnames
        for row in reader:
            string      = row['_Place_of_publication'].strip()
            existing_qid = extract_qid(row.get('P241 Qid', ''))

            if existing_qid:
                row['P241 Qid']   = qid_to_hyperlink(existing_qid)
                row['auto_match'] = ''
                row['vetted']     = row.get('vetted', '').strip()
                _hyperlink_bare_qids(row)
                out_rows.append(row)
                unchanged += 1
                continue

            if string not in candidates:
                row['P241 Qid']   = ''
                row['auto_match'] = ''
                row['vetted']     = row.get('vetted', '').strip()
                _hyperlink_bare_qids(row)
                out_rows.append(row)
                skipped += 1
                continue

            c = candidates[string]

            if c['qid']:
                # Normal single match
                row['P241 Qid']    = qid_to_hyperlink(c['qid'])
                row['P241_values'] = c['label']
                row['auto_match']  = auto_match_note(c['match_type'])
                row['vetted']      = row.get('vetted', '').strip() or vetted_value(c['match_type'])
                _hyperlink_bare_qids(row)
                out_rows.append(row)
                filled += 1

            elif c['parts']:
                # Compound with LLM-resolved parts — emit one row per part
                for part_info in c['parts']:
                    part_row = dict(row)
                    part_qid   = part_info.get('qid', '')
                    part_label = part_info.get('label', '')
                    part_str   = part_info.get('part', '')
                    if part_qid:
                        part_row['P241 Qid']    = qid_to_hyperlink(part_qid)
                        part_row['P241_values'] = part_label
                        filled += 1
                    else:
                        part_row['P241 Qid']    = ''
                        part_row['P241_values'] = ''
                        skipped += 1
                    part_row['auto_match'] = f'compound — split ({part_str})'
                    part_row['vetted']     = ''
                    _hyperlink_bare_qids(part_row)
                    out_rows.append(part_row)

            else:
                # No match (none, compound without parts, rejected)
                row['P241 Qid']   = ''
                row['auto_match'] = auto_match_note(c['match_type'])
                row['vetted']     = ''
                _hyperlink_bare_qids(row)
                out_rows.append(row)
                skipped += 1

    # --- Write output ---
    out_fieldnames = list(in_fieldnames)
    if 'auto_match' not in out_fieldnames:
        out_fieldnames.append('auto_match')
    if 'vetted' not in out_fieldnames:
        out_fieldnames.append('vetted')
    with open(args.out, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=out_fieldnames,
                                delimiter='\t', extrasaction='ignore')
        writer.writeheader()
        writer.writerows(out_rows)

    print(f'Writing merged sheet: {args.out}  ({len(out_rows)} rows)')
    print(f'  filled in    : {filled}')
    print(f'  already had  : {unchanged}')
    print(f'  no candidate : {skipped}')


def _hyperlink_bare_qids(row):
    """Make any bare QID in any cell (except P241 Qid) clickable."""
    for key in row:
        if key != 'P241 Qid':
            row[key] = hyperlink_if_qid(row[key])


if __name__ == '__main__':
    main()
