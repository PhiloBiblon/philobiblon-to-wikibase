"""
extract_gold_seed.py — extract Charles's irreplaceable edits from the old Reference Sources
spreadsheet and write a gold seed TSV for use in generate_basis_mapping.py.

Compares the original upload (old) against Charles's edited version (new).
Only rows Charles actually changed are kept.  Rows whose changes are now handled
by parse rules in the pipeline are excluded:

  year_back      — year moved from loc back into key  (auth_year rule handles this)
  auth_year_loc  — key:page split into key + loc      (auth_year_loc rule handles this)
  roman_lower    — lowercase roman moved to loc        (roman_lower rule handles this)
  bnm            — BNM/BNE shelfmark normalisation    (separate QS fix in FactGrid)

What remains is Charles's domain knowledge: direct QID assignments, corrected
search strings, and comments that can't be automated.

Usage (from pb2wb/):
    python prop_migration/extract_gold_seed.py \\
        --old prop_migration/reference_source.old.tsv \\
        --new prop_migration/reference_source.new.tsv \\
        --out prop_migration/reference_source.gold_seed.tsv
"""

import argparse
import csv
import re
import sys
import os

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.dirname(dir_path))

_QID_RE      = re.compile(r'^Q\d+$')
_YEAR_RE     = re.compile(r'^\d{4}$')
_BNM_RE      = re.compile(r'^BNM\s|^BNE\s+\d')
_ROMAN_RE    = re.compile(r'^[ivxlcdm]+$')


def load_tsv(path):
    with open(path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f, delimiter='\t'))
    return {r['basis']: r for r in rows}, rows


def is_year_back(b, orig, edit):
    """Year was in loc, Charles moved it back into key. auth_year rule now handles this."""
    ok, ol = orig.get('key', ''), orig.get('loc', '')
    ek, el = edit.get('key', ''), edit.get('loc', '')
    return (
        _YEAR_RE.match(ol.strip())
        and ek.strip() == (ok.strip() + ' ' + ol.strip())
        and el.strip() == ''
        and edit.get('Comment', '') == orig.get('Comment', '')
    )


def is_auth_year_loc(b, orig, edit):
    """Orig had no loc; edit split Author YYYY:page into key + loc. auth_year_loc rule handles this."""
    ok, ol = orig.get('key', ''), orig.get('loc', '')
    ek, el = edit.get('key', ''), edit.get('loc', '')
    return (
        not ol.strip()
        and el.strip()
        and not _ROMAN_RE.match(el.strip())   # roman locs handled by is_roman_lower
        and ok.strip() == b
        and not _QID_RE.match(ek.strip())
    )


def is_roman_lower(b, orig, edit):
    """Lowercase roman numeral moved to loc. roman_lower rule now handles this."""
    ok = orig.get('key', '')
    el = edit.get('loc', '')
    ol = orig.get('loc', '')
    return (
        _ROMAN_RE.match(el.strip())
        and ok.strip() == b
        and el.strip() != ol.strip()
    )


def is_bnm(b, orig, edit):
    """BNM/BNE shelfmark normalisation — to be fixed directly in FactGrid via QS."""
    return bool(_BNM_RE.match(b))


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--old', required=True,
                        help='Original TSV uploaded to Charles (before his edits)')
    parser.add_argument('--new', required=True,
                        help='TSV downloaded after Charles made his edits')
    parser.add_argument('--out', default='prop_migration/reference_source.gold_seed.tsv',
                        help='Output gold seed TSV (default: prop_migration/reference_source.gold_seed.tsv)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print stats without writing output')
    args = parser.parse_args()

    orig_map, _      = load_tsv(args.old)
    edit_map, edit_rows = load_tsv(args.new)

    added   = {b for b in edit_map if b not in orig_map}
    changed = {b for b in edit_map if b in orig_map and
               any(edit_map[b].get(c, '') != orig_map[b].get(c, '')
                   for c in ['key', 'loc', 'Comment'])}

    gold_basis = added | changed

    skipped = {'year_back': [], 'auth_year_loc': [], 'roman_lower': [], 'bnm': []}
    gold = []

    for r in edit_rows:
        b = r['basis']
        if b not in gold_basis:
            continue
        o = orig_map.get(b, {})
        if is_year_back(b, o, r):
            skipped['year_back'].append(b)
        elif is_auth_year_loc(b, o, r):
            skipped['auth_year_loc'].append(b)
        elif is_roman_lower(b, o, r):
            skipped['roman_lower'].append(b)
        elif is_bnm(b, o, r):
            skipped['bnm'].append(b)
        else:
            gold.append(r)

    print(f'Changes detected: {len(gold_basis)} ({len(added)} added, {len(changed)} changed)')
    for cat, items in skipped.items():
        print(f'  skipped ({cat:15s}): {len(items)}')
    print(f'Gold seed rows:   {len(gold)}')

    if not args.dry_run:
        fieldnames = list(edit_rows[0].keys()) if edit_rows else ['freq', 'basis', 'key', 'loc', 'Comment']
        with open(args.out, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
            w.writeheader()
            w.writerows(gold)
        print(f'Written: {args.out}')
    else:
        print('[dry-run] no file written')


if __name__ == '__main__':
    main()
