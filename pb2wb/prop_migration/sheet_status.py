"""
sheet_status.py — per-basis FactGrid status for the P721 vetting sheet.

Computed entirely from local records (no FactGrid requests):
  - basis_migration_progress.jsonl   what was converted, with which QID
  - reference_corrections.jsonl      later corrections to those references
  - the latest P721-live.*.tsv       P721 usages still unconverted
  - P721-P129.tsv (sheet pull)       Charles's current QIDs, to spot needed corrections
  - held_bases.tsv (optional)        basis<TAB>reason for work deliberately on hold

Written to the sheet by `sync_sheet.py --pipeline p721 status`, into columns to the
right of Charles's, which he should not edit.
"""

import csv
import glob
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

from prop_migration.correct_references import build_plan, load_sheet, sheet_target

PROGRESS_LOG    = 'prop_migration/basis_migration_progress.jsonl'
CORRECTIONS_LOG = 'prop_migration/reference_corrections.jsonl'
HELD_TSV        = 'prop_migration/held_bases.tsv'
LIVE_GLOB       = 'prop_migration/P721-live*.tsv'

FG_ITEM = 'https://database.factgrid.de/wiki/Item:'
_HTML_TAG_RE = re.compile(r'<[^>]+>')

COL_STATUS    = 'FG status (auto)'
COL_QID       = 'FG qid (auto)'
COL_CONVERTED = 'FG converted (auto)'
COL_REMAINING = 'FG remaining (auto)'
COL_EXAMPLE   = 'Example item (auto)'
STATUS_COLUMNS = [COL_STATUS, COL_QID, COL_CONVERTED, COL_REMAINING, COL_EXAMPLE]


def _strip(basis):
    return _HTML_TAG_RE.sub('', basis or '').strip()


def latest_live_export(pattern=LIVE_GLOB):
    files = sorted(glob.glob(pattern), key=os.path.getmtime)
    return files[-1] if files else None


def load_live(path):
    counts = Counter()
    if path:
        delim = ',' if path.endswith('.csv') else '\t'
        with open(path, newline='', encoding='utf-8-sig') as f:
            for r in csv.DictReader(f, delimiter=delim):
                counts[_strip(r.get('value'))] += int(r.get('freq') or 0)
    return counts


def load_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as f:
        return [json.loads(l) for l in f if l.strip()]


def load_held(path=HELD_TSV):
    held = {}
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    basis, _, reason = line.rstrip('\n').partition('\t')
                    held[basis.strip()] = reason.strip() or 'on hold'
    return held


def compute_status(progress, corrections, live, sheet, held, live_ts=''):
    """
    Return {basis: {column: value}} for every basis in the sheet.

    progress / corrections: lists of log dicts; live: Counter basis -> remaining;
    sheet: basis -> rows (load_sheet); held: basis -> reason.
    live_ts: ISO UTC time of the live export; conversions logged after it are
    subtracted from the remaining counts.
    """
    # Effective QID per converted statement: as written, unless corrected since.
    latest = {}
    for p in progress:
        latest[p['guid']] = p
    corrected = {}
    for c in corrections:
        if c.get('status') in ('corrected', 'already'):
            corrected[c['guid']] = c
    by_basis = defaultdict(list)          # basis -> [(guid, item, qid, ts)]
    for guid, p in latest.items():
        qid = corrected[guid]['new_qid'] if guid in corrected else p.get('qid', '')
        by_basis[_strip(p['basis'])].append((guid, p['item'], qid, p.get('ts', '')))

    # Statements whose reference no longer matches the sheet.
    plan, _ = build_plan([dict(p, guid=g) for g, p in latest.items() if g not in corrected],
                         sheet, {})
    needs_fix = Counter(r['basis'] for r in plan)

    since_export = Counter(b for b, ss in by_basis.items()
                           for *_, t in ss if live_ts and t > live_ts)

    out = {}
    for basis, rows in sheet.items():
        stmts = by_basis.get(basis, [])
        remaining = max(0, live.get(basis, 0) - since_export.get(basis, 0))
        qids = Counter(q for _, _, q, _ in stmts)
        n_corrected = sum(1 for g, *_ in stmts if g in corrected)
        sheet_state = sheet_target(rows)[0]

        if not stmts and not remaining:
            status = ''
        elif basis in held:
            status = f'held: {held[basis]}'
        elif stmts and sheet_state == 'unvetted':
            status = 'needs review: converted, QID since cleared'
        elif needs_fix.get(basis):
            status = f'needs correction ({needs_fix[basis]})'
        elif not stmts:
            status = 'not started'
        elif remaining:
            status = 'partly converted'
        elif n_corrected:
            status = 'corrected'
        else:
            status = 'converted'

        last_ts = max((t for *_, t in stmts), default='')
        example = stmts[0][1] if stmts else ''
        out[basis] = {
            COL_STATUS:    status,
            COL_QID:       ', '.join(q if len(qids) == 1 else f'{q} ({n})'
                                     for q, n in qids.most_common()),
            COL_CONVERTED: f'{len(stmts)} ({last_ts[:10]})' if stmts else '',
            COL_REMAINING: remaining if (stmts or remaining) else '',
            COL_EXAMPLE:   f'=HYPERLINK("{FG_ITEM}{example}","{example}")' if example else '',
        }
    return out


def build(sheet_tsv, live_path=None):
    """Convenience wrapper: load everything from the default locations."""
    live_path = live_path or latest_live_export()
    live_ts = (datetime.fromtimestamp(os.path.getmtime(live_path), timezone.utc).isoformat()
               if live_path else '')
    status = compute_status(load_jsonl(PROGRESS_LOG), load_jsonl(CORRECTIONS_LOG),
                            load_live(live_path), load_sheet(sheet_tsv), load_held(), live_ts)
    return status, live_path
