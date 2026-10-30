"""
correct_references.py — fix P129 references already written by the P721 migration
when the vetting sheet has since changed (group B1: QID re-pointed to another
item; B7: locator added or changed), or move them to another reference property
(physical evidence: P129 "According to" → P702 "Based on", same item).

Two steps:

  plan   (local only) Compare every converted statement in the progress log with
         the current sheet and write a correction plan TSV for review. Trim the
         file by hand to control what gets applied.
         With --move-to P702 --qids FILE, instead plan moving every converted
         reference whose target is one of the QIDs in FILE from P129 to P702.

  apply  For each item in the plan: read it, find the reference on each listed
         statement whose P129 is the old QID, replace it with P129 = new QID plus
         the sheet's locator (other snaks in that reference are kept), and write
         the item once. Every outcome is logged to the corrections log, and
         statements already corrected are skipped, so it is safe to re-run.

Usage (from pb2wb/):
    python prop_migration/correct_references.py plan
    python prop_migration/correct_references.py plan --move-to P702 --qids prop_migration/evidence_qids.tsv \
        --out prop_migration/move_plan_p702.tsv
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
from prop_migration.locators import LOC_PROP, locator_snaks, repair_loc

SHEET_TSV       = 'prop_migration/P721-P129.tsv'
PROGRESS_LOG    = 'prop_migration/basis_migration_progress.jsonl'
TARGET_TYPES    = 'prop_migration/target_types.tsv'
PLAN_TSV        = 'prop_migration/correction_plan.tsv'
CORRECTIONS_LOG = 'prop_migration/reference_corrections.jsonl'
P129            = 'P129'
P702            = 'P702'

QID_RE = re.compile(r'^Q\d+$')
_HTML_TAG_RE = re.compile(r'<[^>]+>')
NEW_ITEM_FLOOR = 2_000_000   # QIDs above this were created recently (mostly by Charles)

PLAN_COLUMNS = ['kind', 'basis', 'item', 'guid', 'prop', 'old_qid', 'old_label',
                'new_qid', 'new_label', 'old_loc', 'loc_type', 'loc', 'old_prop', 'new_prop']

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
    targets = {((r.get('qid') or '').strip(), repair_loc(r.get('basis', ''), r.get('loc')),
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
        ref_prop = p.get('ref_prop', P129)
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
            'old_prop': ref_prop, 'new_prop': ref_prop,
        })
    plan.sort(key=lambda r: (r['kind'], r['basis'], r['item'], r['guid']))
    return plan, skipped


def current_targets(progress, corrections):
    """
    guid -> dict(item, basis, prop, qid, loc, loc_type, ref_prop) as FactGrid has it
    now: the latest progress-log entry, overlaid with later applied corrections.
    """
    cur = {}
    for p in progress:
        cur[p['guid']] = {'item': p['item'], 'basis': p['basis'], 'prop': p.get('prop', ''),
                          'qid': p.get('qid', ''), 'loc': (p.get('loc') or '').strip(),
                          'loc_type': p.get('loc_type', ''),
                          'ref_prop': p.get('ref_prop', P129)}
    for c in corrections:
        t = cur.get(c.get('guid'))
        if t is None or c.get('status') not in ('corrected', 'already'):
            continue
        t.update(qid=c['new_qid'], loc=(c.get('loc') or '').strip(),
                 loc_type=c.get('loc_type', ''), ref_prop=c.get('new_prop', P129))
    return cur


def build_move_plan(progress, corrections, qids, to_prop, labels):
    """
    Plan moving references whose target is in qids from P129 to to_prop (same item,
    same locator). Returns plan rows.
    """
    plan = []
    for guid, t in current_targets(progress, corrections).items():
        if t['qid'] not in qids or t['ref_prop'] == to_prop:
            continue
        plan.append({
            'kind': f'move_{to_prop}', 'basis': _HTML_TAG_RE.sub('', t['basis']).strip(),
            'item': t['item'], 'guid': guid, 'prop': t['prop'],
            'old_qid': t['qid'], 'old_label': labels.get(t['qid'], ''),
            'new_qid': t['qid'], 'new_label': labels.get(t['qid'], ''),
            'old_loc': t['loc'], 'loc_type': t['loc_type'], 'loc': t['loc'],
            'old_prop': t['ref_prop'], 'new_prop': to_prop,
        })
    plan.sort(key=lambda r: (r['old_qid'], r['basis'], r['item'], r['guid']))
    return plan


def load_qids(path):
    """QIDs from the first column of a file (# comments and a header line allowed)."""
    with open(path, encoding='utf-8') as f:
        return {l.split('\t')[0].strip() for l in f
                if QID_RE.match(l.split('\t')[0].strip())}


def _load_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as f:
        return [json.loads(l) for l in f if l.strip()]


def cmd_plan(args):
    progress = _load_jsonl(args.progress_log)
    if args.move_to:
        if not args.qids:
            sys.exit('--move-to needs --qids FILE')
        plan, skipped = build_move_plan(progress, _load_jsonl(args.corrections_log),
                                        load_qids(args.qids), args.move_to,
                                        load_labels(TARGET_TYPES)), Counter()
    else:
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
    if skipped:
        print('left out (not written):')
    for k, n in skipped.most_common():
        print(f'  {k:30} {n:6}')


# ---------------------------------------------------------------------------
# apply (FactGrid)
# ---------------------------------------------------------------------------

def _ref_values(ref, prop=P129):
    out = []
    for snak in ref.snaks.get(prop) or []:
        dv = snak.datavalue
        val = dv.get('value', {}) if isinstance(dv, dict) else {}
        if isinstance(val, dict) and val.get('id'):
            out.append(val['id'])
    return out


def _p129_values(ref):
    return _ref_values(ref, P129)


WRITTEN = ('corrected', 'added')     # outcomes that change the claim


def correct_claim(claim, old_qid, new_qid, loc, loc_type, old_prop=P129, new_prop=P129):
    """
    Replace the reference on claim whose old_prop is old_qid with one whose new_prop
    is new_qid (plus locator). Returns one of 'corrected', 'already', 'missing'.
    With no old_qid (B6: the other sources of a compound basis), add the reference
    alongside the existing ones instead: 'added', or 'present' if it is there already.
    Mutates claim in place.
    """
    from wikibaseintegrator.datatypes import Item as WBItem, String as WBString
    from wikibaseintegrator.models import Reference

    refs = claim.references.references
    if not old_qid:
        if any(new_qid in _ref_values(r, new_prop) for r in refs):
            return 'present'
        new_ref = Reference()
        new_ref.add(WBItem(value=new_qid, prop_nr=new_prop))
        for prop, value in locator_snaks(loc, loc_type):
            new_ref.add(WBString(value=value, prop_nr=prop))
        claim.references.add(new_ref)
        return 'added'
    old_idx = next((i for i, r in enumerate(refs) if old_qid in _ref_values(r, old_prop)), None)
    if old_idx is None:
        new_present = any(new_qid in _ref_values(r, new_prop) for r in refs)
        return 'already' if new_present else 'missing'

    old_ref = refs[old_idx]
    new_snaks = locator_snaks(loc, loc_type)
    replaced_props = {old_prop, new_prop} | {p for p, _ in new_snaks}
    new_ref = Reference()
    new_ref.add(WBItem(value=new_qid, prop_nr=new_prop))
    for prop, value in new_snaks:
        new_ref.add(WBString(value=value, prop_nr=prop))
    for snak in old_ref.snaks:              # keep anything else that was in the block
        if snak.property_number not in replaced_props:
            new_ref.snaks.add(snak)
    refs[old_idx] = new_ref
    return 'corrected'


def verify_claim(claim, old_qid, new_qid, loc, loc_type, old_prop=P129, new_prop=P129):
    """True if claim has a reference with new_prop=new_qid (+ locator) and none with old_prop=old_qid."""
    if ((old_prop, old_qid) != (new_prop, new_qid)
            and any(old_qid in _ref_values(r, old_prop) for r in claim.references)):
        return False
    want = set(locator_snaks(loc, loc_type))
    for r in claim.references:
        if new_qid in _ref_values(r, new_prop):
            have = {(sn.property_number, sn.datavalue.get('value'))
                    for sn in r.snaks
                    if isinstance(sn.datavalue, dict) and isinstance(sn.datavalue.get('value'), str)}
            if want <= have:
                return True
    return False


def should_verify(n, every, first=3):
    """Read back the first few written items, then every Nth."""
    return n <= first or (every > 0 and n % every == 0)


def _props(row):
    return row.get('old_prop') or P129, row.get('new_prop') or P129


def done_key(row):
    """Key a plan row is skipped by once done; an added reference is keyed by its QID too,
    since one statement can get several (and may also have had a B1 fix)."""
    key = (row['guid'], row.get('new_prop') or P129)
    return key + (row['new_qid'],) if row.get('old_qid') == '' else key


def load_corrected(path):
    """done_key()s already applied, so a P702 move isn't skipped after a B1 fix."""
    done = set()
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get('status') in ('corrected', 'already', 'added', 'present'):
                    done.add(done_key(r))
    return done


def log_correction(path, row, status, dry_run):
    if dry_run:
        return
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps({
            'guid': row['guid'], 'item': row['item'], 'basis': row['basis'],
            'old_qid': row['old_qid'], 'new_qid': row['new_qid'],
            'loc': row['loc'], 'loc_type': row['loc_type'],
            'old_prop': _props(row)[0], 'new_prop': _props(row)[1], 'status': status,
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
        if done_key(r) not in done:
            by_item.setdefault(r['item'], []).append(r)
    items = list(by_item.items())
    if args.limit_items:
        items = items[:args.limit_items]
    log.info('Plan: %d statements on %d items (%d already corrected, skipped)%s',
             sum(len(v) for _, v in items), len(items),
             len(done & {done_key(r) for r in plan}),
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
                      correct_claim(claim, r['old_qid'], r['new_qid'], r['loc'], r['loc_type'],
                                    *_props(r)))
            outcomes.append((r, status))
            old_prop, new_prop = _props(r)
            log.info('[%d/%d] %s  %s  %s=%s → %s=%s%s  %s', n, len(items), item_id, r['guid'],
                     old_prop, r['old_qid'], new_prop, r['new_qid'],
                     f" ({r['loc_type']}: {r['loc']})" if r['loc'] else '', status)
        if any(s in WRITTEN for _, s in outcomes) and not args.dry_run:
            try:
                time.sleep(args.delay)
                abm._write_item(item, wbi)
            except Exception as e:
                log.error('%s: write failed: %s', item_id, e)
                outcomes = [(r, 'error' if s in WRITTEN else s) for r, s in outcomes]
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
                            if s not in WRITTEN:
                                continue
                            ok = (r['guid'] in claims and verify_claim(
                                claims[r['guid']], r['old_qid'], r['new_qid'], r['loc'], r['loc_type'],
                                *_props(r)))
                            totals['verified_ok' if ok else 'verified_FAILED'] += 1
                            if not ok:
                                log.error('%s  %s: READ-BACK FAILED', item_id, r['guid'])
                        log.info('%s: read-back checked', item_id)
        for r, s in outcomes:
            log_correction(args.corrections_log, r, s, args.dry_run)
            totals[s] += 1

    log.info('=== %s ===', 'Dry run complete' if args.dry_run else 'Done')
    for k in ('corrected', 'already', 'added', 'present', 'missing', 'error'):
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
    p.add_argument('--move-to', choices=(P702,), metavar='PID',
                   help='plan moving references to this property (P702) instead of sheet corrections')
    p.add_argument('--qids', metavar='FILE', help='with --move-to: target QIDs to move (first column)')
    p.add_argument('--corrections-log', default=CORRECTIONS_LOG)
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
