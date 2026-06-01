#!/usr/bin/env python3
"""
apply_basis_migration.py — Convert P721 string qualifiers to P129 item references.

Reads vetted rows from P721-P129.tsv. For each targeted basis string, finds all
FactGrid statements carrying pq:P721=<basis>, adds a P129=<qid> reference (with
optional locator), then removes the P721 qualifier.

Progress is logged per statement GUID in basis_migration_progress.jsonl — every
run is fully resumable and idempotent.

Usage (from pb2wb/):
  # Dry run — show what would happen
  python prop_migration/apply_basis_migration.py --basis "Faulhaber" --dry-run

  # Single-item pilot
  python prop_migration/apply_basis_migration.py --basis "Faulhaber" --item Q1086703

  # Capped run
  python prop_migration/apply_basis_migration.py --basis "Faulhaber" --max-statements 500

  # Full run
  python prop_migration/apply_basis_migration.py --basis "Faulhaber"
"""

import argparse
import csv
import json
import logging
import os
import random
import sys
import time
from datetime import datetime, timezone

import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from wikibaseintegrator.datatypes import Item as WBItem, String as WBString
from wikibaseintegrator.models import Reference
from common.settings import TEMP_DICT
TEMP_DICT['TEMP_WB'] = 'FACTGRID'
from common.wb_manager import WBManager

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SPARQL_ENDPOINT = 'https://database.factgrid.de/sparql'
API_ENDPOINT    = 'https://database.factgrid.de/w/api.php'
P721            = 'P721'
P129            = 'P129'
PROGRESS_LOG    = 'prop_migration/basis_migration_progress.jsonl'
CANDIDATES_TSV  = 'prop_migration/P721-P129.tsv'
DEFAULT_DELAY   = 2.0   # seconds between item writes
MAX_RETRIES     = 5
RETRY_BACKOFF   = 30    # seconds (doubles each retry, capped at 300)

LOC_PROP = {
    'page':     'P54',
    'folio':    'P100',
    'number':   'P90',
    'footnote': 'P90',
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Progress log
# ---------------------------------------------------------------------------

def load_done_guids(path):
    """Return set of statement GUIDs already successfully converted."""
    done = set()
    if not os.path.exists(path):
        return done
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                done.add(json.loads(line)['guid'])
            except (json.JSONDecodeError, KeyError):
                pass
    return done


def log_progress(path, guid, item_id, basis, qid, loc, loc_type):
    """Append one converted-statement record to the progress log."""
    rec = {
        'guid':     guid,
        'item':     item_id,
        'basis':    basis,
        'qid':      qid,
        'loc':      loc,
        'loc_type': loc_type,
        'ts':       datetime.now(timezone.utc).isoformat(),
    }
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')


# ---------------------------------------------------------------------------
# Candidate lookup
# ---------------------------------------------------------------------------

def load_candidate(basis_str, tsv_path):
    """
    Return the first vetted=Y row for basis_str from the candidates TSV,
    as dict {qid, loc, loc_type}. Returns None if not found or not vetted.
    Warns if multiple vetted rows exist (compound basis — only first is used).
    """
    if not os.path.exists(tsv_path):
        log.error('Candidates TSV not found: %s', tsv_path)
        return None

    matches = []
    with open(tsv_path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            if row.get('basis', '').strip() != basis_str:
                continue
            if row.get('vetted', '').strip() not in ('Y', 'y'):
                continue
            qid = row.get('qid', '').strip()
            if not qid or not qid.startswith('Q'):
                continue
            matches.append({
                'qid':      qid,
                'loc':      row.get('loc', '').strip(),
                'loc_type': row.get('loc_type', '').strip(),
            })

    if not matches:
        return None
    if len(matches) > 1:
        log.warning(
            '%r has %d vetted rows (compound basis?). '
            'Using first: qid=%s. Only one P129 reference will be added.',
            basis_str, len(matches), matches[0]['qid'],
        )
    return matches[0]


# ---------------------------------------------------------------------------
# Network helpers
# ---------------------------------------------------------------------------

def ping_api(timeout=10):
    """Return True if the FactGrid API is reachable."""
    try:
        r = requests.get(API_ENDPOINT,
                         params={'action': 'query', 'format': 'json'},
                         timeout=timeout)
        return r.status_code == 200
    except requests.RequestException:
        return False


def _call_with_retry(fn):
    """
    Call fn(). On requests.RequestException, retry with exponential backoff,
    logging a maintenance-window warning. Other exceptions propagate immediately.
    """
    backoff = RETRY_BACKOFF
    for attempt in range(MAX_RETRIES):
        try:
            return fn()
        except requests.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                log.warning(
                    'Connection error — possible FactGrid maintenance window: %s. '
                    'Retrying in %ds (attempt %d/%d).',
                    e, backoff, attempt + 1, MAX_RETRIES,
                )
                time.sleep(backoff)
                backoff = min(backoff * 2, 300)
            else:
                raise


# ---------------------------------------------------------------------------
# SPARQL
# ---------------------------------------------------------------------------

def find_items(basis_str, item_filter=None):
    """Return list of item QIDs carrying pq:P721=basis_str."""
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
}}"""
    for attempt in range(3):
        try:
            r = requests.post(
                SPARQL_ENDPOINT,
                data={'query': q, 'format': 'json'},
                headers={'User-Agent': 'PB apply_basis_migration/2'},
                timeout=60,
            )
            r.raise_for_status()
            return [b['item']['value'].split('/')[-1]
                    for b in r.json()['results']['bindings']]
        except requests.RequestException as e:
            if attempt < 2:
                log.warning('SPARQL error (%s), retrying in 10s...', e)
                time.sleep(10)
            else:
                raise


def spot_check(basis_str, ref_qid, item_ids, n=5):
    """
    ASK-based SPARQL spot-check on a random sample of converted items.
    Verifies P129=ref_qid is present and P721=basis_str is absent.
    Returns (ok, fail) counts.
    """
    sample = random.sample(sorted(item_ids), min(n, len(item_ids)))
    safe   = basis_str.replace('\\', '\\\\').replace('"', '\\"')
    ok = fail = 0
    for item_id in sample:
        q = f"""
PREFIX pq: <https://database.factgrid.de/prop/qualifier/>
PREFIX pr: <https://database.factgrid.de/prop/reference/>
PREFIX wd: <https://database.factgrid.de/entity/>
ASK {{
  wd:{item_id} ?prop ?stmt .
  ?stmt pr:{P129} wd:{ref_qid} .
  FILTER NOT EXISTS {{ ?stmt pq:{P721} "{safe}" }}
}}"""
        try:
            r = requests.post(
                SPARQL_ENDPOINT,
                data={'query': q, 'format': 'json'},
                headers={'User-Agent': 'PB apply_basis_migration/2'},
                timeout=30,
            )
            if r.json().get('boolean', False):
                ok += 1
                log.info('  spot-check %s: OK', item_id)
            else:
                fail += 1
                log.warning('  spot-check %s: FAILED (P129 absent or P721 still present)',
                            item_id)
        except Exception as e:
            log.warning('  spot-check %s: error (%s)', item_id, e)
    return ok, fail


# ---------------------------------------------------------------------------
# Claim-level helpers
# ---------------------------------------------------------------------------

def _find_p721_snak(claim, basis_str):
    """Return the first P721 qualifier snak matching basis_str, or None."""
    for snak in claim.qualifiers.get(P721) or []:
        dv = snak.datavalue
        if isinstance(dv, dict) and dv.get('value') == basis_str:
            return snak
    return None


def _ref_present(claim, ref_qid):
    """True if any reference on claim already contains P129=ref_qid."""
    for ref in claim.references:
        for snak in ref.snaks.get(P129) or []:
            dv  = snak.datavalue
            val = dv.get('value', {}) if isinstance(dv, dict) else {}
            if isinstance(val, dict) and val.get('id') == ref_qid:
                return True
    return False


# ---------------------------------------------------------------------------
# Item processing
# ---------------------------------------------------------------------------

def process_item(wbi, item_id, basis_str, ref_qid, loc, loc_type,
                 done_guids, dry_run, delay, progress_path):
    """
    Convert all P721=basis_str qualifiers on item_id to P129=ref_qid references.

    Two-phase write:
      Phase 1 — add P129 references (one item write)
      Phase 2 — remove P721 qualifiers (one item write)
    If Phase 1 fails, Phase 2 is not attempted.

    Returns (converted, skipped, errors).
    """
    loc_prop = LOC_PROP.get(loc_type) if loc_type else None
    loc_desc = (f'  loc={loc!r} ({loc_type} → {loc_prop})') if loc else ''

    # ---- Fetch item ----
    try:
        item = _call_with_retry(lambda: wbi.item.get(item_id))
    except Exception as e:
        log.error('%s: fetch failed: %s', item_id, e)
        return 0, 0, 1

    # ---- Classify claims ----
    to_add  = []   # (guid, claim) — need ref added
    already = []   # (guid, claim) — ref already present, just need qual removed
    n_skip  = 0

    for claim in item.claims:
        if _find_p721_snak(claim, basis_str) is None:
            continue
        guid = claim.id
        prop = getattr(getattr(claim, 'mainsnak', None), 'property_number', '?')
        if guid in done_guids:
            n_skip += 1
            log.info('%s  %-36s prop=%-5s  already done — skipping', item_id, guid, prop)
            continue
        if _ref_present(claim, ref_qid):
            already.append((guid, claim))
            log.info('%s  %-36s prop=%-5s  ref exists, qual may still be present',
                     item_id, guid, prop)
        else:
            to_add.append((guid, claim))

    if not to_add and not already:
        if n_skip == 0:
            log.info('%s: no matching statements', item_id)
        return 0, n_skip, 0

    if dry_run:
        for guid, claim in to_add:
            prop = getattr(getattr(claim, 'mainsnak', None), 'property_number', '?')
            log.info('[dry-run] %s  %-36s prop=%-5s  → P129=%s%s',
                     item_id, guid, prop, ref_qid, loc_desc)
        return len(to_add), n_skip, 0

    # ---- Phase 1: add P129 references ----
    for guid, claim in to_add:
        ref = Reference()
        ref.add(WBItem(value=ref_qid, prop_nr=P129))
        if loc and loc_prop:
            ref.add(WBString(value=loc, prop_nr=loc_prop))
        claim.references.add(ref)

    try:
        time.sleep(delay)
        _call_with_retry(lambda: item.write())
        log.info('%s: Phase 1 done — added P129 ref to %d statement(s)', item_id, len(to_add))
    except Exception as e:
        log.error('%s: Phase 1 write (add refs) failed: %s', item_id, e)
        return 0, n_skip, len(to_add)

    # ---- Phase 2: remove P721 qualifiers ----
    # Process to_add + already (ref was pre-existing; qualifier may still be there).
    all_guids = [guid for guid, _ in to_add] + [guid for guid, _ in already]

    try:
        item = _call_with_retry(lambda: wbi.item.get(item_id))
    except Exception as e:
        log.error('%s: Phase 2 fetch failed (refs WERE added): %s', item_id, e)
        return 0, n_skip, len(all_guids)

    removed = []
    for guid in all_guids:
        claim = next((c for c in item.claims if c.id == guid), None)
        if claim is None:
            log.error('%s  %s: claim not found on Phase 2 fetch', item_id, guid)
            continue
        snak = _find_p721_snak(claim, basis_str)
        if snak is None:
            log.info('%s  %-36s  P721 qual already absent', item_id, guid)
            removed.append(guid)
            continue
        claim.qualifiers.remove(snak)
        removed.append(guid)

    try:
        time.sleep(delay)
        _call_with_retry(lambda: item.write())
        log.info('%s: Phase 2 done — removed P721 qual from %d statement(s)',
                 item_id, len(removed))
    except Exception as e:
        log.error('%s: Phase 2 write (remove quals) failed (refs WERE added): %s',
                  item_id, e)
        return 0, n_skip, len(removed)

    # ---- Log progress ----
    converted = 0
    for guid in removed:
        log_progress(progress_path, guid, item_id, basis_str, ref_qid, loc, loc_type)
        log.info('CONVERTED  %s  %s%s', item_id, guid, loc_desc)
        converted += 1

    return converted, n_skip, 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description='Convert P721 string qualifiers to P129 item references.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument('--basis', required=True,
                    help='P721 string value to migrate, e.g. "Faulhaber"')
    ap.add_argument('--item', metavar='QID',
                    help='Restrict to one item (for piloting)')
    ap.add_argument('--max-statements', type=int, default=None, metavar='N',
                    help='Stop after converting N statements this run')
    ap.add_argument('--dry-run', action='store_true',
                    help='Log what would be done without writing to FactGrid')
    ap.add_argument('--delay', type=float, default=DEFAULT_DELAY, metavar='SECS',
                    help=f'Seconds between item writes (default: {DEFAULT_DELAY})')
    ap.add_argument('--progress-log', default=PROGRESS_LOG, metavar='PATH',
                    help=f'JSONL progress file (default: {PROGRESS_LOG})')
    ap.add_argument('--tsv', default=CANDIDATES_TSV, metavar='PATH',
                    help=f'Candidates TSV (default: {CANDIDATES_TSV})')
    args = ap.parse_args()

    # ---- Look up case ----
    case = load_candidate(args.basis, args.tsv)
    if case is None:
        sys.exit(
            f"ERROR: '{args.basis}' not found in {args.tsv} with vetted=Y "
            f"and a valid QID.\n"
            f"Check: row exists, vetted='Y', qid starts with 'Q'."
        )
    ref_qid  = case['qid']
    loc      = case['loc']
    loc_type = case['loc_type']

    log.info('Basis    : %r  →  P129=%s', args.basis, ref_qid)
    if loc:
        log.info('Locator  : %r  (%s  →  %s)',
                 loc, loc_type, LOC_PROP.get(loc_type, 'unknown prop'))
    log.info('Mode     : %s', 'DRY RUN' if args.dry_run else 'EXECUTE')
    if args.item:
        log.info('Item     : %s  (single-item pilot)', args.item)
    if args.max_statements:
        log.info('Cap      : %d statements max', args.max_statements)

    # ---- Ping API ----
    if not args.dry_run:
        log.info('Pinging FactGrid API...')
        if not ping_api():
            sys.exit(
                'ERROR: FactGrid API is not reachable. '
                'Aborting — check for a maintenance window and retry later.'
            )
        log.info('  reachable.')

    # ---- Load progress ----
    done_guids = load_done_guids(args.progress_log)
    log.info('Progress : %d GUIDs already done', len(done_guids))

    # ---- Find items ----
    log.info('Finding items via SPARQL...')
    items = find_items(args.basis, args.item)
    log.info('  %d item(s) found', len(items))
    if not items:
        log.info('Nothing to do.')
        return

    # ---- Connect ----
    try:
        wbm = WBManager()
        wbi = wbm.get_wbi()
    except Exception as e:
        if args.dry_run:
            log.info('WBManager unavailable (%s).', e)
            log.info('Shallow dry-run: %d items found via SPARQL — done.', len(items))
            return
        sys.exit(f'ERROR: Cannot connect to FactGrid: {e}')

    # ---- Process items ----
    total_converted = total_skipped = total_errors = 0
    converted_item_ids = set()

    for item_id in items:
        if args.max_statements is not None and total_converted >= args.max_statements:
            log.info('Reached --max-statements %d — stopping early.', args.max_statements)
            break

        log.info('--- %s ---', item_id)
        converted, skipped, errors = process_item(
            wbi, item_id, args.basis, ref_qid, loc, loc_type,
            done_guids, args.dry_run, args.delay, args.progress_log,
        )
        total_converted += converted
        total_skipped   += skipped
        total_errors    += errors

        if converted > 0:
            converted_item_ids.add(item_id)
            done_guids = load_done_guids(args.progress_log)

    # ---- Summary ----
    log.info('')
    log.info('=== Run complete ===')
    log.info('Converted : %d statement(s)', total_converted)
    log.info('Skipped   : %d (already done)', total_skipped)
    log.info('Errors    : %d', total_errors)
    if total_errors:
        log.warning('There were errors — review the log above before continuing.')

    # ---- Spot-check ----
    if not args.dry_run and converted_item_ids:
        log.info('')
        log.info('SPARQL spot-check on %d item(s)...', min(5, len(converted_item_ids)))
        ok, fail = spot_check(args.basis, ref_qid, converted_item_ids)
        log.info('Spot-check: %d OK, %d FAILED', ok, fail)
        if fail:
            log.warning(
                'Spot-check failures — investigate before running further batches.'
            )


if __name__ == '__main__':
    main()
