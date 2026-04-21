"""
parse_basis_values.py — Phase 1 of P721 bootstrap: parse raw values into
structured key + loc + col_* columns without any FactGrid API calls.

Run after fetch_basis_values.py.  The output TSV is consumed by
lookup_basis_keys.py.  Because this step makes no network calls you can
re-run it freely while tuning parse patterns.

Usage (from pb2wb/):
    python prop_migration/parse_basis_values.py
    python prop_migration/parse_basis_values.py --limit 200
    python prop_migration/parse_basis_values.py --dry-run
    python prop_migration/parse_basis_values.py --values prop_migration/P721-raw-values.tsv
    python prop_migration/parse_basis_values.py --out prop_migration/P721-parsed.tsv
"""

import os
import sys
import csv
import argparse

dir_path = os.path.dirname(os.path.realpath(__file__))
parent_dir_path = os.path.dirname(dir_path)
sys.path.append(parent_dir_path)

from prop_migration.generate_basis_mapping import parse_loc_columns, preprocess

VALUES_TSV = 'prop_migration/P721-raw-values.tsv'
PARSED_TSV = 'prop_migration/P721-parsed.tsv'

PARSE_COLUMNS = [
    'freq', 'basis', 'key',
    'loc', 'loc_type', 'preproc_type', 'parse_pattern',
    'col_folio', 'col_page', 'col_volume', 'col_date', 'col_footnote', 'col_literal',
]


def load_raw_values(tsv_path, limit=None):
    rows = []
    with open(tsv_path, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            rows.append((row['value'], int(row['freq'])))
            if limit and len(rows) >= limit:
                break
    return rows


def parse_value(raw, freq):
    pp = preprocess(raw)
    return {
        'freq':          freq,
        'basis':         pp['basis'],
        'key':           pp['key'],
        'loc':           pp['loc'],
        'loc_type':      pp['loc_type'],
        'preproc_type':  pp['preproc_type'],
        'parse_pattern': pp['parse_pattern'],
        **parse_loc_columns(pp['loc'], pp['loc_type'], pp['parse_pattern']),
    }


def main():
    parser = argparse.ArgumentParser(
        description='Phase 1: parse P721 raw values into key/loc/col_* columns')
    parser.add_argument('--values',  default=VALUES_TSV,
                        help=f'Raw values TSV from fetch_basis_values.py (default: {VALUES_TSV})')
    parser.add_argument('--out',     default=PARSED_TSV,
                        help=f'Output parsed TSV (default: {PARSED_TSV})')
    parser.add_argument('--limit',   type=int, default=None,
                        help='Process only the top N values (default: all)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show parse results without writing output')
    args = parser.parse_args()

    if not os.path.exists(args.values):
        print(f'Error: {args.values} not found.')
        print('Run first:  python prop_migration/fetch_basis_values.py')
        sys.exit(1)

    raw_values = load_raw_values(args.values, args.limit)
    limit_msg = f'top {args.limit}' if args.limit else 'all'
    print(f'Loaded {len(raw_values)} values ({limit_msg}) from {args.values}')

    parsed = [parse_value(raw, freq) for raw, freq in raw_values]

    excluded  = [r for r in parsed if r['preproc_type'] == 'excluded']
    compound  = [r for r in parsed if r['preproc_type'] == 'compound']
    to_search = [r for r in parsed if r['preproc_type'] == '']

    from collections import Counter
    pattern_counts = Counter(r['parse_pattern'] for r in to_search)
    has_loc = sum(1 for r in to_search if r['loc'])

    print(f'  excluded : {len(excluded)}  compound : {len(compound)}  to search: {len(to_search)}')
    print(f'  has loc  : {has_loc} of {len(to_search)} ({100*has_loc//max(len(to_search),1)}%)')
    print(f'  patterns : { {k: v for k, v in pattern_counts.most_common()} }')

    unique_keys = len({r['key'] for r in to_search})
    print(f'  unique keys: {unique_keys} (API calls saved by dedup: {len(to_search) - unique_keys})')

    if args.dry_run:
        print()
        for r in to_search[:20]:
            print(f"  [{r['parse_pattern']:14s}] key={r['key']!r:35s} loc={r['loc']!r}")
        if len(to_search) > 20:
            print(f'  ... ({len(to_search) - 20} more)')
        print('\n(dry-run: no output written)')
        return

    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    with open(args.out, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=PARSE_COLUMNS, delimiter='\t')
        writer.writeheader()
        writer.writerows(parsed)

    print(f'\nWritten: {args.out}  ({len(parsed)} rows)')
    print(f'Next step: python prop_migration/lookup_basis_keys.py --parsed {args.out}')


if __name__ == '__main__':
    main()
