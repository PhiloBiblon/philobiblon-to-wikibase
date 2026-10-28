"""
swap_qualifier.py — replace a P721 qualifier with a different qualifier on the
same statement (no reference involved), for P721 strings that describe the
statement itself rather than its source.

Charles's decisions (2026-10-27):
  uncertainty  "?" / "[?]"           → P155 "How sure is this?" = Q160240 "Uncertain"
  foliation    "fol. mod.", ...      → P1243 "Physical description" (monolingual text)

For each statement carrying P721 = <basis> (and its HTML variants): add the new
qualifier unless an identical one is already there, remove the P721 qualifier,
and write the item once — so the two changes land together or not at all.
Statements that no longer carry the P721 are simply not found again, so a re-run
picks up only what is left.

Usage (from pb2wb/):
    python prop_migration/swap_qualifier.py --basis '?' --basis '[?]' \\
        --qualifier P155 --item-value Q160240 --dry-run
    python prop_migration/swap_qualifier.py --basis 'fol. mod.' \\
        --qualifier P1243 --text-from-basis --lang es --limit-items 5
"""

import argparse
import json
import logging
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

SWAP_LOG = 'prop_migration/qualifier_swaps.jsonl'

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested)
# ---------------------------------------------------------------------------

def _snak_value(snak):
    dv = snak.datavalue
    if not isinstance(dv, dict):
        return None
    v = dv.get('value')
    if isinstance(v, dict) and 'id' in v:
        return v['id']                                   # item
    if isinstance(v, dict) and 'text' in v:
        return (v['text'], v.get('language'))           # monolingual text
    return v                                            # string


def wanted_value(spec, basis):
    """The value the new qualifier should have, in _snak_value form."""
    if spec['item']:
        return spec['item']
    text = basis if spec['text_from_basis'] else spec['text']
    return (text, spec['lang'])


def make_snak(spec, basis):
    from wikibaseintegrator.datatypes import Item as WBItem, MonolingualText
    if spec['item']:
        return WBItem(value=spec['item'], prop_nr=spec['prop'])
    text, lang = wanted_value(spec, basis)
    return MonolingualText(text=text, language=lang, prop_nr=spec['prop'])


def swap_on_claim(claim, basis_variant, spec, canonical_basis, p721_snak_finder):
    """
    Swap P721=basis_variant for the new qualifier on one claim (in place).
    Returns 'swapped', 'no_p721'.  If an identical new qualifier already exists,
    only the P721 is removed (still 'swapped').
    """
    snak = p721_snak_finder(claim, basis_variant)
    if snak is None:
        return 'no_p721'
    want = wanted_value(spec, canonical_basis)
    present = any(_snak_value(s) == want for s in claim.qualifiers.get(spec['prop']) or [])
    if not present:
        claim.qualifiers.add(make_snak(spec, canonical_basis))
    claim.qualifiers.remove(snak)
    return 'swapped'


def verify_claim(claim, basis_variant, spec, canonical_basis, p721_snak_finder):
    """True if the P721 is gone and the new qualifier is present."""
    if p721_snak_finder(claim, basis_variant) is not None:
        return False
    want = wanted_value(spec, canonical_basis)
    return any(_snak_value(s) == want for s in claim.qualifiers.get(spec['prop']) or [])


def should_verify(n, every, first=3):
    return n <= first or (every > 0 and n % every == 0)


def log_swap(path, guid, item, prop, basis, spec, dry_run):
    if dry_run:
        return
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps({
            'guid': guid, 'item': item, 'prop': prop, 'basis': basis,
            'qualifier': spec['prop'],
            'value': spec['item'] or (basis if spec['text_from_basis'] else spec['text']),
            'lang': spec['lang'] if not spec['item'] else '',
            'ts': datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False) + '\n')


# ---------------------------------------------------------------------------
# FactGrid run
# ---------------------------------------------------------------------------

def run(args, spec):
    import prop_migration.apply_basis_migration as abm   # sets TEMP_WB=FACTGRID, logging

    if not args.dry_run:
        log.info('Pinging FactGrid API...')
        if not abm.ping_api():
            log.error('FactGrid API is not reachable — check for a maintenance window.')
            return 1
    wbi = abm.connect()

    totals = Counter()
    n_written = 0
    n_items = 0
    consecutive_failures = 0
    for basis in args.basis:
        for variant in abm.find_raw_variants(basis):
            items = abm.find_items(variant)
            log.info('Basis %r%s: %d item(s)', basis,
                     f' (variant {variant!r})' if variant != basis else '', len(items))
            for item_id in items:
                if args.limit_items and n_items >= args.limit_items:
                    log.info('Reached --limit-items %d', args.limit_items)
                    break
                n_items += 1
                try:
                    item = abm._call_with_retry(lambda: wbi.item.get(item_id), wbi=wbi)
                except Exception as e:
                    log.error('%s: fetch failed: %s', item_id, e)
                    totals['error'] += 1
                    consecutive_failures += 1
                    if consecutive_failures >= 3:
                        log.error('3 items failed in a row — stopping (maintenance window?). Re-run later.')
                        return 1
                    continue

                swapped = []
                for claim in item.claims:
                    if swap_on_claim(claim, variant, spec, basis, abm._find_p721_snak) == 'swapped':
                        prop = getattr(getattr(claim, 'mainsnak', None), 'property_number', '?')
                        swapped.append((claim.id, prop))
                if not swapped:
                    log.info('%s: no matching statements', item_id)
                    continue
                for guid, prop in swapped:
                    log.info('%s%s  %s  prop=%-6s P721 %r → %s', '[dry-run] ' if args.dry_run else '',
                             item_id, guid, prop, variant,
                             f"{spec['prop']}={wanted_value(spec, basis)!r}")
                if args.dry_run:
                    totals['would_swap'] += len(swapped)
                    continue
                try:
                    time.sleep(args.delay)
                    abm._write_item(item, wbi)
                except Exception as e:
                    log.error('%s: write failed: %s', item_id, e)
                    totals['error'] += len(swapped)
                    consecutive_failures += 1
                    if consecutive_failures >= 3:
                        log.error('3 items failed in a row — stopping (maintenance window?). Re-run later.')
                        return 1
                    continue
                consecutive_failures = 0
                n_written += 1
                for guid, prop in swapped:
                    log_swap(args.log, guid, item_id, prop, basis, spec, args.dry_run)
                totals['swapped'] += len(swapped)

                if should_verify(n_written, args.verify_every):
                    try:
                        check = abm._call_with_retry(lambda: wbi.item.get(item_id), wbi=wbi)
                    except Exception as e:
                        log.warning('%s: read-back failed: %s', item_id, e)
                    else:
                        claims = {c.id: c for c in check.claims}
                        for guid, _ in swapped:
                            ok = guid in claims and verify_claim(
                                claims[guid], variant, spec, basis, abm._find_p721_snak)
                            totals['verified_ok' if ok else 'verified_FAILED'] += 1
                            if not ok:
                                log.error('%s  %s: READ-BACK FAILED', item_id, guid)
            else:
                continue
            break   # --limit-items reached

    log.info('=== %s ===', 'Dry run complete' if args.dry_run else 'Done')
    for k in ('would_swap', 'swapped', 'error', 'verified_ok', 'verified_FAILED'):
        if totals[k]:
            log.info('  %-16s %d', k, totals[k])
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    ap.add_argument('--basis', action='append', required=True,
                    help='P721 string to swap (repeatable); HTML variants are found automatically')
    ap.add_argument('--qualifier', required=True, metavar='PID', help='new qualifier property')
    val = ap.add_mutually_exclusive_group(required=True)
    val.add_argument('--item-value', metavar='QID', help='item value for the new qualifier')
    val.add_argument('--text-value', metavar='TEXT', help='fixed monolingual-text value')
    val.add_argument('--text-from-basis', action='store_true',
                     help='use the P721 string itself as the monolingual-text value')
    ap.add_argument('--lang', default='es', help='language for monolingual text (default es)')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--limit-items', type=int, default=None, metavar='N')
    ap.add_argument('--delay', type=float, default=1.0, metavar='SECS',
                    help='seconds before each item write (default 1.0)')
    ap.add_argument('--verify-every', type=int, default=10, metavar='N',
                    help='read back the first 3 written items, then every Nth (default 10)')
    ap.add_argument('--log', default=SWAP_LOG)
    args = ap.parse_args()
    spec = {'prop': args.qualifier, 'item': args.item_value, 'text': args.text_value,
            'text_from_basis': args.text_from_basis, 'lang': args.lang}
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%H:%M:%S')
    sys.exit(run(args, spec))


if __name__ == '__main__':
    main()
