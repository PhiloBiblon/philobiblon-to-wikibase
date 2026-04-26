#!/usr/bin/env python3
"""
apply_basis_migration.py — Convert P721 string qualifiers to P129 item references.

For each targeted (basis_string, p129_qid) pair, finds all statements on the
target item(s) carrying pq:P721=<basis>, adds a P129=<qid> reference (with an
optional locator qualifier if loc/loc_type are set), and removes the P721
qualifier. All changes to one item are batched into a single fetch+write.

Usage (dry run — default):
  python prop_migration/apply_basis_migration.py --basis Faulhaber --item Q1086703
  python prop_migration/apply_basis_migration.py --basis "Perea 2004" --item Q425307

Execute for real:
  python prop_migration/apply_basis_migration.py --basis Faulhaber --item Q1086703 --execute
"""

import argparse
import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import requests

from wikibaseintegrator.datatypes import Item as WBItem, String as WBString
from wikibaseintegrator.models import Reference
from common.settings import TEMP_DICT
TEMP_DICT['TEMP_WB'] = 'FACTGRID'
from common.wb_manager import WBManager

SPARQL_ENDPOINT = 'https://database.factgrid.de/sparql'
P721 = 'P721'
P129 = 'P129'
WRITE_DELAY = 1.0   # seconds between item writes

# loc_type → FactGrid locator property
LOC_PROP = {
    'page':     'P54',
    'folio':    'P100',
    'number':   'P90',
    'footnote': 'P90',
}

# Handpicked cases: P721 string value → reference info.
# Required: qid (P129 target).
# Optional: loc (locator string), loc_type (page/folio/number/footnote).
CASES = {
    'Faulhaber':        {'qid': 'Q164508'},
    'Perea 2004':       {'qid': 'Q1071227'},
    '<i>DHEE</i> 2400':  {'qid': 'Q426064',  'loc': '2400', 'loc_type': 'page'},
    'Catalán 1974:34n': {'qid': 'Q1068207', 'loc': '34n',  'loc_type': 'footnote'},
}


def find_items(basis_str, item_filter=None):
    """Return distinct item QIDs that have at least one pq:P721=basis_str statement."""
    bind = f'BIND(wd:{item_filter} AS ?item)' if item_filter else ''
    safe = basis_str.replace('\\', '\\\\').replace('"', '\\"')
    q = f"""
PREFIX p:  <https://database.factgrid.de/prop/>
PREFIX pq: <https://database.factgrid.de/prop/qualifier/>
PREFIX wd: <https://database.factgrid.de/entity/>

SELECT DISTINCT ?item WHERE {{
  {bind}
  ?item ?prop ?stmt .
  ?stmt pq:{P721} "{safe}" .
}}
"""
    r = requests.post(SPARQL_ENDPOINT,
                      data={'query': q, 'format': 'json'},
                      headers={'User-Agent': 'PB apply_basis_migration'})
    r.raise_for_status()
    return [b['item']['value'].split('/')[-1]
            for b in r.json()['results']['bindings']]


def build_reference(ref_qid, loc, loc_type):
    """
    Build a Reference with P129=ref_qid and, if loc is non-empty, a locator snak.
    """
    ref = Reference()
    ref.add(WBItem(value=ref_qid, prop_nr=P129))
    if loc and loc_type in LOC_PROP:
        ref.add(WBString(value=loc, prop_nr=LOC_PROP[loc_type]))
    return ref


def process_item(wbi, item_id, basis_str, ref_qid, loc, loc_type, dry_run):
    """
    Fetch item, find all claims with pq:P721=basis_str, add reference and remove
    the P721 qualifier from each. One write per item.
    Returns number of statements modified.
    """
    item = wbi.item.get(item_id)
    targets = []   # (claim, target_snak)

    for claim in item.claims:
        snaks = claim.qualifiers.get(P721) or []
        for snak in snaks:
            dv = snak.datavalue
            val = dv.get('value') if isinstance(dv, dict) else None
            if val == basis_str:
                targets.append((claim, snak))
                break   # at most one P721 per statement

    if not targets:
        print(f'  {item_id}: no matching statements found')
        return 0

    loc_desc = f'  loc={loc!r} ({loc_type})' if loc else ''
    for claim, snak in targets:
        prop = claim.mainsnak.property_number if hasattr(claim, 'mainsnak') else '?'
        print(f'  {item_id}  {claim.id}  prop={prop}{loc_desc}', end='')
        if dry_run:
            print('  [dry-run]')
        else:
            ref = build_reference(ref_qid, loc, loc_type)
            claim.references.add(ref)
            claim.qualifiers.remove(snak)
            print('  → reference added, qualifier removed')

    if not dry_run:
        time.sleep(WRITE_DELAY)
        item.write()
        print(f'  wrote {item_id} ({len(targets)} statement(s) updated)')

    return len(targets)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--basis', required=True,
                    help='P721 string value, e.g. "Faulhaber"')
    ap.add_argument('--item',
                    help='Restrict to a single item QID, e.g. Q1086703')
    ap.add_argument('--execute', action='store_true',
                    help='Write to FactGrid (default is dry-run)')
    args = ap.parse_args()

    if args.basis not in CASES:
        sys.exit(f"ERROR: '{args.basis}' not in CASES. Keys: {list(CASES)}")

    case = CASES[args.basis]
    ref_qid  = case['qid']
    loc      = case.get('loc', '')
    loc_type = case.get('loc_type', '')
    dry_run  = not args.execute

    print(f'Basis    : {args.basis!r} → P129={ref_qid}')
    if loc:
        print(f'Locator  : {loc!r} ({loc_type}) → {LOC_PROP.get(loc_type, "unknown prop")}')
    print(f'Mode     : {"DRY RUN" if dry_run else "EXECUTE"}')
    if args.item:
        print(f'Item     : {args.item}')

    print('Finding items via SPARQL ...')
    items = find_items(args.basis, args.item)
    print(f'  {len(items)} item(s)')

    if not items:
        print('Nothing to do.')
        return

    wbm = WBManager()
    wbi = wbm.get_wbi()

    total = 0
    for item_id in items:
        n = process_item(wbi, item_id, args.basis, ref_qid, loc, loc_type, dry_run)
        total += n

    verb = 'modified' if not dry_run else 'would be modified'
    print(f'\nTotal: {total} statement(s) {verb}.')


if __name__ == '__main__':
    main()
