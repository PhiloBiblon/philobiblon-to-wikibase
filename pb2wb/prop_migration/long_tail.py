"""
long_tail.py — the long-tail plan (agreed with Charles 2026-11-01): replace every
remaining P721 qualifier with a reference that keeps the original text:

    P129 According to = PhiloBiblon (Q398957)
    P73  Note         = the P721 string, word for word (HTML included)

Reversible: when a string is identified later, correct_references.py swaps
PhiloBiblon for the real work.

Two steps:

  export  One SPARQL query for every statement still carrying P721 on an item with
          a PhiloBiblon ID (P476; other FactGrid projects use P721 too): writes a plan
          TSV (item, guid, prop, basis) sorted by item. Trim it by hand to control
          what gets applied.

  apply   For each item in the plan: read it once; on each listed statement, for
          each listed P721 value, add the reference (unless an identical one is
          already there), then remove that P721 qualifier; write the item once, so
          the two changes land together or not at all. Every outcome is logged, and
          statements already done are skipped, so it is safe to re-run.

Usage (from pb2wb/):
    python prop_migration/long_tail.py export
    python prop_migration/long_tail.py apply --plan prop_migration/long_tail_plan.tsv --dry-run --limit-items 5
    python prop_migration/long_tail.py apply --plan prop_migration/long_tail_plan.tsv --limit-items 5
"""

import argparse
import csv
import io
import json
import logging
import os
import sys
import time
from collections import Counter, OrderedDict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

PLAN_TSV     = 'prop_migration/long_tail_plan.tsv'
LONG_TAIL_LOG = 'prop_migration/long_tail.jsonl'
SPARQL_ENDPOINT = 'https://database.factgrid.de/sparql'
PHILOBIBLON  = 'Q398957'
P129, P73, P721 = 'P129', 'P73', 'P721'

PLAN_COLUMNS = ['item', 'guid', 'prop', 'basis']

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested)
# ---------------------------------------------------------------------------

def guid_from_uri(uri):
    """Statement URI (…/statement/Q123-ABC-…) → claim id (Q123$ABC-…)."""
    local = uri.rsplit('/', 1)[-1]
    item, _, rest = local.partition('-')
    return f'{item.upper()}${rest}'


def _snak_str(snak):
    dv = snak.datavalue
    return dv.get('value') if isinstance(dv, dict) and isinstance(dv.get('value'), str) else None


def _snak_item_id(snak):
    dv = snak.datavalue
    v = dv.get('value') if isinstance(dv, dict) else None
    return v.get('id') if isinstance(v, dict) else None


def find_p721(claim, basis):
    """The P721 qualifier snak on claim whose value is exactly basis, or None."""
    return next((s for s in claim.qualifiers.get(P721) or [] if _snak_str(s) == basis), None)


def ref_present(claim, basis):
    """True if claim already has a reference with P129=PhiloBiblon and P73=basis."""
    for ref in claim.references:
        if (any(_snak_item_id(s) == PHILOBIBLON for s in ref.snaks.get(P129) or [])
                and any(_snak_str(s) == basis for s in ref.snaks.get(P73) or [])):
            return True
    return False


def convert_claim(claim, basis):
    """
    Replace P721=basis on claim with the PhiloBiblon reference (in place).
    The reference is added before the qualifier is removed. Returns 'converted',
    or 'gone' when the claim no longer carries that P721 value.
    """
    from wikibaseintegrator.datatypes import Item as WBItem, String as WBString
    from wikibaseintegrator.models import Reference

    snak = find_p721(claim, basis)
    if snak is None:
        return 'gone'
    if not ref_present(claim, basis):
        ref = Reference()
        ref.add(WBItem(value=PHILOBIBLON, prop_nr=P129))
        ref.add(WBString(value=basis, prop_nr=P73))
        claim.references.add(ref)
    claim.qualifiers.remove(snak)
    return 'converted'


def verify_claim(claim, basis):
    """True if the P721 is gone and the PhiloBiblon reference is there."""
    return find_p721(claim, basis) is None and ref_present(claim, basis)


def should_verify(n, every, first=3):
    return n <= first or (every > 0 and n % every == 0)


def done_key(row):
    return (row['guid'], row['basis'])


def load_done(path):
    done = set()
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get('status') in ('converted', 'gone'):
                    done.add(done_key(r))
    return done


def group_by_item(plan, done):
    """OrderedDict item -> rows not yet done, in plan order."""
    by_item = OrderedDict()
    for r in plan:
        if done_key(r) not in done:
            by_item.setdefault(r['item'], []).append(r)
    return by_item


def log_outcome(path, row, status, dry_run):
    if dry_run:
        return
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps({
            'guid': row['guid'], 'item': row['item'], 'prop': row['prop'],
            'basis': row['basis'], 'status': status,
            'ts': datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False) + '\n')


# ---------------------------------------------------------------------------
# export (one SPARQL query)
# ---------------------------------------------------------------------------

EXPORT_QUERY = """
PREFIX pq: <https://database.factgrid.de/prop/qualifier/>
PREFIX wdt: <https://database.factgrid.de/prop/direct/>
SELECT ?item ?p ?stmt ?basis WHERE {
  ?stmt pq:P721 ?basis .
  ?item ?p ?stmt .
  FILTER EXISTS { ?item wdt:P476 [] }
}"""


def cmd_export(args):
    import requests
    import common.factgrid_access as fa   # noqa: F401  (patches requests: UA, throttle, reputation)

    # CSV, not JSON: some P721 strings hold raw newlines, which break FactGrid's JSON output
    r = requests.post(SPARQL_ENDPOINT, data={'query': EXPORT_QUERY},
                      headers={'Accept': 'text/csv'}, timeout=600)
    r.raise_for_status()
    r.encoding = 'utf-8'
    if 'Exception' in r.text[-5000:]:
        raise RuntimeError('SPARQL query failed on the server (timeout?): ' + r.text[-300:])
    rows = []
    for b in csv.DictReader(io.StringIO(r.text, newline='')):
        rows.append({'item': b['item'].rsplit('/', 1)[-1],
                     'guid': guid_from_uri(b['stmt']),
                     'prop': b['p'].rsplit('/', 1)[-1],      # …/prop/P21
                     'basis': b['basis']})
    rows.sort(key=lambda r: (int(r['item'][1:]), r['guid'], r['basis']))
    with open(args.out, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=PLAN_COLUMNS, delimiter='\t', lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    log.info('wrote %s: %d statements/values, %d items, %d distinct strings (reputation %s)',
             args.out, len(rows), len({r['item'] for r in rows}),
             len({r['basis'] for r in rows}), fa.reputation(r))


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------

def cmd_apply(args):
    import prop_migration.apply_basis_migration as abm   # sets TEMP_WB=FACTGRID, logging
    from common.wb_manager import WBManager

    with open(args.plan, newline='', encoding='utf-8') as f:
        plan = list(csv.DictReader(f, delimiter='\t'))
    done = load_done(args.log)
    items = list(group_by_item(plan, done).items())
    if args.limit_items:
        items = items[:args.limit_items]
    log.info('Plan: %d statements/values on %d items (%d already done, skipped)%s',
             sum(len(v) for _, v in items), len(items),
             len(done & {done_key(r) for r in plan}),
             '  [DRY RUN]' if args.dry_run else '')
    if not items:
        return 0

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
                return 1
            continue
        claims = {c.id: c for c in item.claims}
        outcomes = []
        for r in rows:
            claim = claims.get(r['guid'])
            status = 'missing' if claim is None else convert_claim(claim, r['basis'])
            outcomes.append((r, status))
            log.info('%s[%d/%d] %s  %s  %-6s P721 %r → P129=%s + P73  %s',
                     '[dry-run] ' if args.dry_run else '', n, len(items), item_id,
                     r['guid'], r['prop'], r['basis'], PHILOBIBLON, status)
        if any(s == 'converted' for _, s in outcomes) and not args.dry_run:
            try:
                time.sleep(args.delay)
                abm._write_item(item, wbi)
            except Exception as e:
                log.error('%s: write failed: %s', item_id, e)
                outcomes = [(r, 'error' if s == 'converted' else s) for r, s in outcomes]
                for r, s in outcomes:
                    log_outcome(args.log, r, s, args.dry_run)
                    totals[s] += 1
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    log.error('3 items failed in a row — stopping (maintenance window?). Re-run later.')
                    return 1
                continue
            consecutive_failures = 0
            totals['items_written'] += 1
            if should_verify(totals['items_written'], args.verify_every):
                try:
                    check = abm._call_with_retry(lambda: wbi.item.get(item_id), wbi=wbi)
                except Exception as e:
                    log.warning('%s: read-back failed: %s', item_id, e)
                else:
                    back = {c.id: c for c in check.claims}
                    for r, s in outcomes:
                        if s != 'converted':
                            continue
                        ok = r['guid'] in back and verify_claim(back[r['guid']], r['basis'])
                        totals['verified_ok' if ok else 'verified_FAILED'] += 1
                        if not ok:
                            log.error('%s  %s: READ-BACK FAILED', item_id, r['guid'])
        else:
            consecutive_failures = 0
        for r, s in outcomes:
            log_outcome(args.log, r, s, args.dry_run)
            totals[s] += 1

    log.info('=== %s ===', 'Dry run complete' if args.dry_run else 'Done')
    for k in ('converted', 'gone', 'missing', 'error', 'items_written'):
        log.info('  %-14s %d', k, totals[k])
    if not args.dry_run:
        log.info('  read-back: %d statements OK, %d FAILED (sampled items)',
                 totals['verified_ok'], totals['verified_FAILED'])
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    sub = ap.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('export', help='write the plan from one SPARQL query (read-only)')
    e.add_argument('--out', default=PLAN_TSV)
    a = sub.add_parser('apply', help='apply a plan to FactGrid')
    a.add_argument('--plan', default=PLAN_TSV)
    a.add_argument('--dry-run', action='store_true')
    a.add_argument('--limit-items', type=int, default=None, metavar='N')
    a.add_argument('--delay', type=float, default=1.0, metavar='SECS',
                   help='seconds before each item write (default 1.0)')
    a.add_argument('--verify-every', type=int, default=10, metavar='N',
                   help='read back the first 3 written items, then every Nth (default 10; 0 = first 3 only)')
    a.add_argument('--log', default=LONG_TAIL_LOG)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%H:%M:%S')
    sys.exit(cmd_export(args) if args.cmd == 'export' else cmd_apply(args))


if __name__ == '__main__':
    main()
