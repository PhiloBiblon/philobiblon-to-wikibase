"""
match_type_report.py — summarize basis_candidates.tsv by match_type.

Outputs a TSV with columns: match_type, rows, total_freq, meaning

Usage (from pb2wb/):
    python prop_migration/match_type_report.py
    python prop_migration/match_type_report.py --candidates prop_migration/basis_candidates.tsv
    python prop_migration/match_type_report.py --out report.tsv
"""

import argparse
import csv
import sys
from collections import defaultdict

CANDIDATES = 'prop_migration/basis_candidates.tsv'

# Ordered display: confidence levels first, then status categories.
# Within each group, order reflects reliability / actionability.
_GROUPS = [
    ('Confidence (match found)', [
        'vetted',
        'charles_edit',
        'known',
        'api_label',
        'api_alias',
        'key_vetted',
        'api_fuzzy',
    ]),
    ('Status (no match / not applicable)', [
        'none',
        'excluded',
        'shelfmark',
        'legacy',
        'llm_pending',
    ]),
]

_ORDER = [mt for _, mts in _GROUPS for mt in mts]

MEANINGS = {
    # confidence
    'vetted':       'Charles marked vetted=Y — human-approved',
    'charles_edit': 'Key or QID from Charles\'s gold seed edits',
    'api_label':    'Exact FactGrid label match — high confidence',
    'api_alias':    'Exact FactGrid alias match — high confidence',
    'key_vetted':   'Propagated from a Charles-vetted key on another row',
    'known':        'QID from known_qids.tsv — manually curated API miss',
    'api_fuzzy':    'API hit but label differs from search key — needs review',
    # status
    'none':         'Searched but no FactGrid item found — reference likely missing from FG',
    'excluded':     'Not a reference (fol. mod., ?, princeps…) — intentionally skipped',
    'shelfmark':    'Library call number — not searched, needs FG item creation',
    'legacy':       'QID from old Reference Sources spreadsheet — being retired',
    'llm_pending':  'Not yet parsed by LLM — run with --llm to resolve',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--candidates', default=CANDIDATES,
                        help=f'Input TSV (default: {CANDIDATES})')
    parser.add_argument('--out', default='-',
                        help='Output TSV path (default: stdout)')
    args = parser.parse_args()

    rows_by_type  = defaultdict(int)
    freq_by_type  = defaultdict(int)

    with open(args.candidates, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            mt   = row.get('match_type', '').strip()
            freq = row.get('freq', '0').strip()
            try:
                freq_int = int(freq)
            except ValueError:
                freq_int = 0
            rows_by_type[mt] += 1
            freq_by_type[mt] += freq_int

    total_rows = sum(rows_by_type.values())
    total_freq = sum(freq_by_type.values())

    out = open(args.out, 'w', newline='', encoding='utf-8') if args.out != '-' else sys.stdout
    try:
        writer = csv.writer(out, delimiter='\t')
        writer.writerow(['match_type', 'rows', 'total_freq', 'meaning'])
        seen = set()
        for group_label, mts in _GROUPS:
            group_rows = sum(rows_by_type[mt] for mt in mts if mt in rows_by_type)
            group_freq = sum(freq_by_type[mt] for mt in mts if mt in rows_by_type)
            if not group_rows:
                continue
            writer.writerow([f'-- {group_label} --', group_rows, group_freq, ''])
            for mt in mts:
                if mt in rows_by_type:
                    writer.writerow([mt, rows_by_type[mt], freq_by_type[mt], MEANINGS.get(mt, '')])
                    seen.add(mt)
            writer.writerow([f'-- Subtotal --', group_rows, group_freq, ''])
        for mt, count in sorted(rows_by_type.items(), key=lambda x: -x[1]):
            if mt not in seen:
                writer.writerow([mt, count, freq_by_type[mt], MEANINGS.get(mt, '')])
        writer.writerow(['TOTAL', total_rows, total_freq, ''])
    finally:
        if args.out != '-':
            out.close()


if __name__ == '__main__':
    main()
