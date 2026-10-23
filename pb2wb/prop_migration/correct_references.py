"""
correct_references.py — fix P129 references already written by the P721 migration
when the vetting sheet has since changed (group B1: QID re-pointed to another
item; B7: locator added or changed).

Two steps:

  plan   (local only) Compare every converted statement in the progress log with
         the current sheet and write a correction plan TSV for review. Trim the
         file by hand to control what gets applied.

  apply  For each item in the plan: read it, find the reference on each listed
         statement whose P129 is the old QID, replace it with P129 = new QID plus
         the sheet's locator (other snaks in that reference are kept), and write
         the item once. Every outcome is logged to the corrections log, and
         statements already corrected are skipped, so it is safe to re-run.

Usage (from pb2wb/):
    python prop_migration/correct_references.py plan
    python prop_migration/correct_references.py apply --plan prop_migration/correction_plan.tsv --dry-run
    python prop_migration/correct_references.py apply --plan prop_migration/correction_plan.tsv --limit-items 5

Rows the plan leaves out (reported, not written): sheet row no longer vetted or
QID cleared (group B3 — needs Charles), malformed QID, or conflicting vetted
rows for the same basis.
"""

import argparse
import csv
import json
import logging
import os
import re
import sys
import time
from collections import Counter, OrderedDict, defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from common.sheet_fields import is_vetted
from prop_migration.locators import LOC_PROP, locator_snaks

SHEET_TSV       = 'prop_migration/P721-P129.tsv'
PROGRESS_LOG    = 'prop_migration/basis_migration_progress.jsonl'
TARGET_TYPES    = 'prop_migration/target_types.tsv'
PLAN_TSV        = 'prop_migration/correction_plan.tsv'
CORRECTIONS_LOG = 'prop_migration/reference_corrections.jsonl'
P129            = 'P129'

QID_RE = re.compile(r'^Q\d+$')
_HTML_TAG_RE = re.compile(r'<[^>]+>')
NEW_ITEM_FLOOR = 2_000_000   # QIDs above this were created recently (mostly by Charles)

PLAN_COLUMNS = ['kind', 'basis', 'item', 'guid', 'prop', 'old_qid', 'old_label',
                'new_qid', 'new_label', 'old_loc', 'loc_type', 'loc']

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# plan (local)
# ---------------------------------------------------------------------------

def load_sheet(path):
    """basis -> list of rows (a basis can appear on several rows)."""
    rows = defaultdict(list)
    with open(path, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            b = (r.get('basis') or '').strip()
            if b:
                rows[b].append(r)
    return rows


def load_labels(path):
    labels = {}
    if os.path.exists(path):
        with open(path, newline='', encoding='utf-8') as f:
            for r in csv.DictReader(f, delimiter='\t'):
                labels.setdefault(r['item'].rsplit('/', 1)[-1], r.get('itemLabel', ''))
    return labels


def sheet_target(rows):
    """
    Resolve a basis's sheet rows to (status, qid, label, loc, loc_type).
    status: 'ok', 'unvetted', 'bad_qid', 'conflict'.
    """
    vetted = [r for r in rows if is_vetted(r.get('vetted'))]
    if not vetted:
        return 'unvetted', '', '', '', ''
    targets = {((r.get('qid') or '').strip(), (r.get('loc') or '').strip(),
                (r.get('loc_type') or '').strip()) for r in vetted}
    if len(targets) > 1:
        return 'conflict', '', '', '', ''
    qid, loc, loc_type = targets.pop()
    if not QID_RE.match(qid):
        return 'bad_qid', qid, '', loc, loc_type
    return 'ok', qid, vetted[0].get('label', ''), loc, loc_type


def build_plan(progress, sheet, labels):
    """
    progress: iterable of progress-log dicts. Returns (plan_rows, skipped Counter).
    Only the latest entry per GUID counts.
    """
    latest = OrderedDict()
    for p in progress:
        latest[p['guid']] = p
    plan, skipped = [], Counter()
    for guid, p in latest.items():
        basis = _HTML_TAG_RE.sub('', p['basis']).strip()
        rows = sheet.get(basis)
        if not rows:
            skipped['basis not in sheet'] += 1
            continue
        status, qid, label, loc, loc_type = sheet_target(rows)
        if status != 'ok':
            skipped[status] += 1
            continue
        old_qid, old_loc = p.get('qid', ''), (p.get('loc') or '').strip()
        if qid == old_qid and loc == old_loc:
            continue
        if loc and loc_type not in LOC_PROP:
            skipped['locator type has no property'] += 1
            continue
        if qid == old_qid:
            kind = 'locator'
        elif int(qid[1:]) >= NEW_ITEM_FLOOR:
            kind = 'new_item'
        else:
            kind = 'existing_item'
        plan.append({
            'kind': kind, 'basis': basis, 'item': p['item'], 'guid': guid,
            'prop': p.get('prop', ''), 'old_qid': old_qid,
            'old_label': labels.get(old_qid, ''), 'new_qid': qid, 'new_label': label,
            'old_loc': old_loc, 'loc_type': loc_type, 'loc': loc,
        })
    plan.sort(key=lambda r: (r['kind'], r['basis'], r['item'], r['guid']))
    return plan, skipped


def cmd_plan(args):
    with open(args.progress_log, encoding='utf-8') as f:
        progress = [json.loads(l) for l in f if l.strip()]
    plan, skipped = build_plan(progress, load_sheet(args.sheet), load_labels(TARGET_TYPES))
    with open(args.out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=PLAN_COLUMNS, delimiter='\t')
        w.writeheader()
        w.writerows(plan)
    by_kind = Counter(r['kind'] for r in plan)
    print(f'{len(plan)} statements to correct on {len({r["item"] for r in plan})} items, '
          f'{len({r["basis"] for r in plan})} bases -> {args.out}')
    for k, n in by_kind.most_common():
        print(f'  {k:14} {n:5}')
    print('left out (not written):')
    for k, n in skipped.most_common():
        print(f'  {k:30} {n:6}')


# ---------------------------------------------------------------------------
# apply (FactGrid)
# ---------------------------------------------------------------------------

def _p129_values(ref):
    out = []
    for snak in ref.snaks.get(P129) or []:
        dv = snak.datavalue
        val = dv.get('value', {}) if isinstance(dv, dict) else {}
        if isinstance(val, dict) and val.get('id'):
            out.append(val['id'])
    return out


def correct_claim(claim, old_qid, new_qid, loc, loc_type):
    """
    Replace the reference on claim whose P129 is old_qid. Returns one of
    'corrected', 'already', 'missing'. Mutates claim in place.
    """
    from wikibaseintegrator.datatypes import Item as WBItem, String as WBString
    from wikibaseintegrator.models import Reference

    refs = claim.references.references
    old_idx = next((i for i, r in enumerate(refs) if old_qid in _p129_values(r)), None)
    if old_idx is None:
        new_present = any(new_qid in _p129_values(r) for r in refs)
        return 'already' if new_present else 'missing'

    old_ref = refs[old_idx]
    new_snaks = locator_snaks(loc, loc_type)
    replaced_props = {P129} | {p for p, _ in new_snaks}
    new_ref = Reference()
    new_ref.add(WBItem(value=new_qid, prop_nr=P129))
    for prop, value in new_snaks:
        new_ref.add(WBString(value=value, prop_nr=prop))
    for snak in old_ref.snaks:              # keep anything else that was in the block
        if snak.property_number not in replaced_props:
            new_ref.snaks.add(snak)
    refs[old_idx] = new_ref
    return 'corrected'


def verify_claim(claim, old_qid, new_qid, loc, loc_type):
    """True if claim has a reference with P129=new_qid (+ locator) and none with old_qid."""
    if old_qid != new_qid and any(old_qid in _p129_values(r) for r in claim.references):
        return False
    want = set(locator_snaks(loc, loc_type))
    for r in claim.references:
        if new_qid in _p129_values(r):
            have = {(sn.property_number, sn.datavalue.get('value'))
                    for sn in r.snaks
                    if isinstance(sn.datavalue, dict) and isinstance(sn.datavalue.get('value'), str)}
            if want <= have:
                return True
    return False


def should_verify(n, every, first=3):
    """Read back the first few written items, then every Nth."""
    return n <= first or (every > 0 and n % every == 0)


def load_corrected(path):
    done = set()
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get('status') in ('corrected', 'already'):
                    done.add(r['guid'])
    return done


def log_correction(path, row, status, dry_run):
    if dry_run:
        return
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps({
            'guid': row['guid'], 'item': row['item'], 'basis': row['basis'],
            'old_qid': row['old_qid'], 'new_qid': row['new_qid'],
            'loc': row['loc'], 'loc_type': row['loc_type'], 'status': status,
            'ts': datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False) + '\n')


def cmd_apply(args):
    import prop_migration.apply_basis_migration as abm   # sets TEMP_WB=FACTGRID, logging
    from common.wb_manager import WBManager

    with open(args.plan, newline='', encoding='utf-8') as f:
        plan = list(csv.DictReader(f, delimiter='\t'))
    done = load_corrected(args.corrections_log)
    by_item = OrderedDict()
    for r in plan:
        if r['guid'] not in done:
            by_item.setdefault(r['item'], []).append(r)
    items = list(by_item.items())
    if args.limit_items:
        items = items[:args.limit_items]
    log.info('Plan: %d statements on %d items (%d already corrected, skipped)%s',
             sum(len(v) for _, v in items), len(items), len(done & {r['guid'] for r in plan}),
             '  [DRY RUN]' if args.dry_run else '')
    if not items:
        return

    wbm = WBManager()
    wbi = wbm.get_wbi()
    abm._relogin = wbm.relogin

    totals = Counter()
    consecutive_failures = 0
    for n, (item_id, rows) in enumerate(items, 1):
        try:
            item = abm._call_with_retry(lambda: wbi.item.get(item_id), wbi=wbi)
        except Exception as e:
            log.error('[%d/%d] %s: fetch failed: %s', n, len(items), item_id, e)
            totals['error'] += len(rows)
            consecutive_failures += 1
            if consecutive_failures >= 3:
                log.error('3 items failed in a row — stopping (maintenance window?). Re-run later.')
                break
            continue
        outcomes = []
        for r in rows:
            claim = next((c for c in item.claims if c.id == r['guid']), None)
            status = ('missing' if claim is None else
                      correct_claim(claim, r['old_qid'], r['new_qid'], r['loc'], r['loc_type']))
            outcomes.append((r, status))
            log.info('[%d/%d] %s  %s  %s → %s%s  %s', n, len(items), item_id, r['guid'],
                     r['old_qid'], r['new_qid'],
                     f" ({r['loc_type']}: {r['loc']})" if r['loc'] else '', status)
        if any(s == 'corrected' for _, s in outcomes) and not args.dry_run:
            try:
                time.sleep(args.delay)
                abm._write_item(item, wbi)
            except Exception as e:
                log.error('%s: write failed: %s', item_id, e)
                outcomes = [(r, 'error' if s == 'corrected' else s) for r, s in outcomes]
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    for r, s in outcomes:
                        log_correction(args.corrections_log, r, s, args.dry_run)
                    log.error('3 items failed in a row — stopping (maintenance window?). Re-run later.')
                    break
            else:
                consecutive_failures = 0
                n_written = totals['items_written'] = totals['items_written'] + 1
                if should_verify(n_written, args.verify_every):
                    try:
                        check = abm._call_with_retry(lambda: wbi.item.get(item_id), wbi=wbi)
                    except Exception as e:
                        log.warning('%s: read-back failed: %s', item_id, e)
                    else:
                        claims = {c.id: c for c in check.claims}
                        for r, s in outcomes:
                            if s != 'corrected':
                                continue
                            ok = (r['guid'] in claims and verify_claim(
                                claims[r['guid']], r['old_qid'], r['new_qid'], r['loc'], r['loc_type']))
                            totals['verified_ok' if ok else 'verified_FAILED'] += 1
                            if not ok:
                                log.error('%s  %s: READ-BACK FAILED', item_id, r['guid'])
                        log.info('%s: read-back checked', item_id)
        for r, s in outcomes:
            log_correction(args.corrections_log, r, s, args.dry_run)
            totals[s] += 1

    log.info('=== %s ===', 'Dry run complete' if args.dry_run else 'Done')
    for k in ('corrected', 'already', 'missing', 'error'):
        log.info('  %-10s %d', k, totals[k])
    if not args.dry_run:
        log.info('  read-back: %d statements OK, %d FAILED (sampled items)',
                 totals['verified_ok'], totals['verified_FAILED'])
    if totals['missing']:
        log.info('  (missing = old reference not found; see %s)', args.corrections_log)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('plan', help='write a correction plan (local only)')
    p.add_argument('--sheet', default=SHEET_TSV)
    p.add_argument('--progress-log', default=PROGRESS_LOG)
    p.add_argument('--out', default=PLAN_TSV)
    a = sub.add_parser('apply', help='apply a correction plan to FactGrid')
    a.add_argument('--plan', required=True)
    a.add_argument('--dry-run', action='store_true')
    a.add_argument('--limit-items', type=int, default=None, metavar='N')
    a.add_argument('--delay', type=float, default=1.0, metavar='SECS',
                   help='seconds before each item write (default 1.0)')
    a.add_argument('--verify-every', type=int, default=10, metavar='N',
                   help='read back the first 3 written items, then every Nth (default 10; 0 = first 3 only)')
    a.add_argument('--corrections-log', default=CORRECTIONS_LOG)
    args = ap.parse_args()
    if args.cmd == 'plan':
        cmd_plan(args)
    else:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                            datefmt='%H:%M:%S')
        cmd_apply(args)


if __name__ == '__main__':
    main()
