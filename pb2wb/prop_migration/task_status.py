"""
task_status.py — estimate how many P721 usages remain in each task group and
rewrite the numbers table in prop_migration/STATUS.md (between the
<!-- usage-table --> markers). Local only: no FactGrid requests.

Remaining = the latest live-count snapshot (P721-live.<date>.tsv) minus every
conversion or qualifier swap logged after the snapshot was taken.

Usage (from pb2wb/):
    python prop_migration/task_status.py              # print and update STATUS.md
    python prop_migration/task_status.py --print-only
"""

import argparse
import csv
import glob
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

P = 'prop_migration/'
STATUS_MD = P + 'STATUS.md'
ORIGINAL_USAGES = 132259          # all P721 usages at the start of the migration
START, END = '<!-- usage-table -->', '<!-- /usage-table -->'

# Group order = the order we plan to finish them in (cumulative % follows it)
GROUPS = [
    ('A8', 'Foliation → P1243'),
    ('A8b', 'Physical descriptions → P1243'),
    ('A8c', 'Physical notes with a colon → P1243'),
    ('A6', 'Pipeline-approved, awaiting Charles'),
    ('A3', 'Catalogue + evidence combos'),
    ('A2', 'Held: locator mismatch, DHEE vol.'),
    ('held', 'Held bases (B2 works-vs-people, …)'),
    ('A4/A5/A10', 'Vetted, other blockers'),
    ('A9', 'Compounds (X / Y)'),
    ('A7', 'Long tail, no match'),
]

_PHYS = re.compile(r'guard|relligad|reclam|signatur|quadern|ex-?libris|segell|sello|full|plec|enquadern'
                   r'|paper|pergamí|tinta|marge|caplletr|filigrana|cobert|superlibris|escut', re.I)
_CATALOGUE_PREFIX = re.compile(r'^[^:]{2,40}:\s')
_DHEE_VOL = re.compile(r'^DHEE [IV]+:')


def strip_html(s):
    return re.sub(r'<[^>]+>', '', s or '').strip()


def latest_snapshot():
    files = sorted(glob.glob(P + 'P721-live.*.tsv'))
    if not files:
        raise SystemExit('no P721-live.<date>.tsv snapshot found')
    path = files[-1]
    taken = datetime.fromtimestamp(os.path.getmtime(path), timezone.utc)
    return path, taken.isoformat(timespec='seconds')


def load_live(path):
    live = {}
    with open(path, encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            live[r['value']] = int(r['freq'])
    return live


def done_since(since_iso, logs=(P + 'basis_migration_progress.jsonl', P + 'qualifier_swaps.jsonl')):
    """Usages converted or swapped after since_iso, per basis (HTML-stripped)."""
    done = Counter()
    for path in logs:
        if not os.path.exists(path):
            continue
        with open(path, encoding='utf-8') as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get('ts', '') >= since_iso:
                    done[strip_html(r.get('basis', ''))] += 1
    return done


def remaining(live, done):
    """live counts minus done, matched on the HTML-stripped basis."""
    left = dict(live)
    by_canon = defaultdict(list)
    for v in live:
        by_canon[strip_html(v)].append(v)
    for basis, n in done.items():
        for v in by_canon.get(basis, []):
            take = min(left[v], n)
            left[v] -= take
            n -= take
    return {v: n for v, n in left.items() if n > 0}


def _column(path, col=0):
    out = set()
    if not os.path.exists(path):
        return out
    with open(path, encoding='utf-8') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                out.add(strip_html(line.rstrip('\n').split('\t')[col]))
    return out


def _tsv_bases(path):
    if not os.path.exists(path):
        return set()
    with open(path, encoding='utf-8', newline='') as f:
        return {strip_html(r['basis']) for r in csv.DictReader(f, delimiter='\t')}


def load_group_lists():
    vetted = set()
    with open(P + 'P721-P129.tsv', encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            if (r.get('vetted') or '').strip().upper().startswith('Y'):
                vetted.add(strip_html(r['basis']))
    return {
        'A8': _tsv_bases(P + 'a8_foliation.tsv'),
        'A8b': _tsv_bases(P + 'a8b_physical.tsv'),
        'A8c': _tsv_bases(P + 'a8c_physical.tsv'),
        'A3x': _tsv_bases(P + 'a8b_excluded.tsv'),
        'A6': _column(P + 'pipeline_vetted_bases.tsv'),
        'A2': _column(P + 'exclude_locator_mismatch.tsv'),
        'held': _column(P + 'held_bases.tsv'),
        'vetted': vetted,
    }


def classify(raw, lists):
    s = strip_html(raw)
    if s in lists['A8']:
        return 'A8'
    if s in lists['A8b']:
        return 'A8b'
    if s in lists['A8c']:
        return 'A8c'
    if ' / ' in s:
        return 'A9'
    if s in lists['A6']:
        return 'A6'
    if s in lists['A2'] or _DHEE_VOL.match(s):
        return 'A2'
    if s in lists['A3x'] or (_PHYS.search(s) and _CATALOGUE_PREFIX.match(s)):
        return 'A3'
    if s in lists['held']:
        return 'held'
    if s in lists['vetted']:
        return 'A4/A5/A10'
    return 'A7'


def build_table(left, snapshot, since):
    per = Counter()
    lists = load_group_lists()
    for v, n in left.items():
        per[classify(v, lists)] += n
    done_now = ORIGINAL_USAGES - sum(left.values())
    rows = ['| Group | | Usages left | % of original | Cumulative done |',
            '|---|---|---:|---:|---:|',
            f'| *Done* | | {done_now:,} | {done_now / ORIGINAL_USAGES:.1%} | {done_now / ORIGINAL_USAGES:.1%} |']
    cum = done_now
    for key, label in GROUPS:
        cum += per[key]
        rows.append(f'| {key} | {label} | {per[key]:,} | {per[key] / ORIGINAL_USAGES:.1%} '
                    f'| {cum / ORIGINAL_USAGES:.1%} |')
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    rows.append('')
    rows.append(f'_Generated {stamp} by `task_status.py` from `{os.path.basename(snapshot)}` '
                f'(taken {since[:16]} UTC) minus conversions logged since. '
                f'Groups are assigned by list membership and keywords, so small-group '
                f'boundaries are approximate._')
    return '\n'.join(rows)


def update_status_md(table, path=STATUS_MD):
    with open(path, encoding='utf-8') as f:
        text = f.read()
    i, j = text.index(START), text.index(END)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text[:i + len(START)] + '\n' + table + '\n' + text[j:])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    ap.add_argument('--print-only', action='store_true')
    args = ap.parse_args()
    snapshot, since = latest_snapshot()
    left = remaining(load_live(snapshot), done_since(since))
    table = build_table(left, snapshot, since)
    print(table)
    if not args.print_only:
        update_status_md(table)
        print(f'\nupdated {STATUS_MD}')


if __name__ == '__main__':
    main()
