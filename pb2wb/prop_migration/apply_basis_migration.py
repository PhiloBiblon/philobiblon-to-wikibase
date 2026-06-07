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
import signal
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
RAW_VALUES_TSV  = 'prop_migration/P721-raw-values.tsv'
DEFAULT_DELAY   = 2.0   # seconds between item writes
MAX_RETRIES     = 5
RETRY_BACKOFF   = 30    # seconds (doubles each retry, capped at 300)
CALL_TIMEOUT    = 90    # seconds before a hung wbi API call is aborted and retried

import re as _re
_HTML_TAG_RE = _re.compile(r'<[^>]+>')

def strip_html(s):
    return _HTML_TAG_RE.sub('', s).strip()


def find_raw_variants(basis_str, raw_values_path=RAW_VALUES_TSV):
    """
    Return all P721 raw strings from raw_values_path that are HTML-equivalent
    to basis_str (i.e. strip_html(raw) == strip_html(basis_str)).
    Always includes basis_str itself. Falls back to trying <i>basis_str</i>
    if the raw values file is unavailable.
    """
    target = strip_html(basis_str)
    variants = {basis_str}
    if os.path.exists(raw_values_path):
        with open(raw_values_path, newline='', encoding='utf-8') as f:
            for row in csv.reader(f, delimiter='\t'):
                if row and strip_html(row[0]) == target:
                    variants.add(row[0])
    else:
        variants.add(f'<i>{basis_str}</i>')
    return sorted(variants)

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


def log_progress(path, guid, item_id, basis, qid, loc, loc_type, prop='', main_value=''):
    """Append one converted-statement record to the progress log."""
    rec = {
        'guid':       guid,
        'item':       item_id,
        'prop':       prop,
        'main_value': main_value,
        'basis':      basis,
        'qid':        qid,
        'loc':        loc,
        'loc_type':   loc_type,
        'ts':         datetime.now(timezone.utc).isoformat(),
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

    stripped = strip_html(basis_str)
    matches = []
    with open(tsv_path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            row_basis = row.get('basis', '').strip()
            if row_basis != basis_str and row_basis != stripped:
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


class _CallTimeout(Exception):
    pass


def _call_with_retry(fn):
    """
    Call fn() with a per-call timeout (CALL_TIMEOUT seconds). On timeout or
    requests.RequestException, retry with exponential backoff. Other exceptions
    propagate immediately.
    """
    def _handler(signum, frame):
        raise _CallTimeout(f'wbi API call exceeded {CALL_TIMEOUT}s')

    backoff = RETRY_BACKOFF
    for attempt in range(MAX_RETRIES):
        try:
            signal.signal(signal.SIGALRM, _handler)
            signal.alarm(CALL_TIMEOUT)
            try:
                result = fn()
            finally:
                signal.alarm(0)  # cancel alarm whether call succeeded or not
            return result
        except (_CallTimeout, requests.RequestException) as e:
            if attempt < MAX_RETRIES - 1:
                log.warning(
                    'Call failed/timed out — retrying in %ds (attempt %d/%d): %s',
                    backoff, attempt + 1, MAX_RETRIES, e,
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


SPOT_CHECK_LIMIT = 20   # check all GUIDs if ≤ this many, else sample


def api_spot_check(guids, basis_str, ref_qid):
    """
    API-based GUID-level spot-check (no SPARQL propagation lag).

    Checks all GUIDs when ≤ SPOT_CHECK_LIMIT converted this run, otherwise
    samples SPOT_CHECK_LIMIT at random. For each GUID, fetches the statement
    via wbgetclaims and verifies:
      - pr:P129 = ref_qid is present in references
      - pq:P721 = basis_str is absent from qualifiers

    Returns (ok, fail, errors).
    """
    sample = guids if len(guids) <= SPOT_CHECK_LIMIT else random.sample(guids, SPOT_CHECK_LIMIT)
    ok = fail = errors = 0
    for guid in sample:
        item_id = guid.split('$')[0]
        try:
            r = requests.get(
                API_ENDPOINT,
                params={'action': 'wbgetclaims', 'entity': item_id, 'format': 'json'},
                headers={'User-Agent': 'PB apply_basis_migration/2'},
                timeout=30,
            )
            claims = r.json().get('claims', {})
            stmt = None
            for prop_stmts in claims.values():
                for s in prop_stmts:
                    if s.get('id', '').lower() == guid.lower():
                        stmt = s
                        break
                if stmt:
                    break

            if stmt is None:
                log.warning('  spot-check %s: statement not found on item', guid)
                fail += 1
                continue

            has_p129 = any(
                isinstance(snak.get('datavalue', {}).get('value'), dict)
                and snak['datavalue']['value'].get('id') == ref_qid
                for ref in stmt.get('references', [])
                for snak in ref.get('snaks', {}).get(P129, [])
            )
            has_p721 = any(
                snak.get('datavalue', {}).get('value') == basis_str
                for snak in stmt.get('qualifiers', {}).get(P721, [])
            )

            if has_p129 and not has_p721:
                ok += 1
                log.info('  spot-check %s: OK', guid)
            else:
                reasons = []
                if not has_p129:
                    reasons.append('P129 missing')
                if has_p721:
                    reasons.append('P721 still present')
                fail += 1
                log.warning('  spot-check %s: FAILED (%s)', guid, ', '.join(reasons))

        except Exception as e:
            log.warning('  spot-check %s: error (%s)', guid, e)
            errors += 1

    return ok, fail, errors


# ---------------------------------------------------------------------------
# Claim-level helpers
# ---------------------------------------------------------------------------

def _snak_label(claim):
    """Return a compact human-readable string for a claim's main value."""
    try:
        dv = claim.mainsnak.datavalue
        if isinstance(dv, dict):
            v = dv.get('value', '')
            if isinstance(v, dict):
                if 'text' in v:       return v['text']           # monolingualtext
                if 'id' in v:         return v['id']             # wikibase-entityid
                if 'time' in v:       return v['time']           # time
                if 'amount' in v:     return v['amount']         # quantity
            return str(v)
    except Exception:
        pass
    return ''


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
                 done_guids, dry_run, delay, progress_path,
                 canonical_basis=None):
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
        return [], 0, 1

    # ---- Classify claims ----
    to_add  = []   # (guid, claim) — need ref added
    already = []   # (guid, claim) — ref already present, just need qual removed
    n_skip  = 0
    guid_meta = {}  # guid → (prop, main_value) for logging

    for claim in item.claims:
        if _find_p721_snak(claim, basis_str) is None:
            continue
        guid = claim.id
        prop = getattr(getattr(claim, 'mainsnak', None), 'property_number', '?')
        guid_meta[guid] = (prop, _snak_label(claim))
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
        return [], n_skip, 0

    if dry_run:
        for guid, claim in to_add:
            prop = getattr(getattr(claim, 'mainsnak', None), 'property_number', '?')
            log.info('[dry-run] %s  %-36s prop=%-5s  → P129=%s%s',
                     item_id, guid, prop, ref_qid, loc_desc)
        return [guid for guid, _ in to_add], n_skip, 0

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
        err_str = str(e)
        if 'external client site' in err_str and 'did not provide page information' in err_str:
            # Stale sitelink on the item — permanent, not a maintenance window.
            log.warning('%s: skipping — permanent sitelink error (stale external link): %s',
                        item_id, e)
            return [], n_skip, 0
        if 'no longer logged in' in err_str or 'anonymous token' in err_str:
            # Session expired — transient auth failure, not a maintenance window.
            # Item will be retried on next process restart (which re-authenticates).
            log.warning('%s: skipping — auth session expired, will retry on restart: %s',
                        item_id, e)
            return [], n_skip, 0
        log.error('%s: Phase 1 write (add refs) failed: %s', item_id, e)
        return [], n_skip, len(to_add)

    # ---- Phase 2: remove P721 qualifiers ----
    # Process to_add + already (ref was pre-existing; qualifier may still be there).
    all_guids = [guid for guid, _ in to_add] + [guid for guid, _ in already]

    try:
        item = _call_with_retry(lambda: wbi.item.get(item_id))
    except Exception as e:
        log.error('%s: Phase 2 fetch failed (refs WERE added): %s', item_id, e)
        return [], n_skip, len(all_guids)

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
        return [], n_skip, len(removed)

    # ---- Log progress ----
    log_basis = canonical_basis if canonical_basis is not None else basis_str
    converted_guids = []
    for guid in removed:
        prop, main_value = guid_meta.get(guid, ('', ''))
        log_progress(progress_path, guid, item_id, log_basis, ref_qid, loc, loc_type,
                     prop=prop, main_value=main_value)
        log.info('CONVERTED  %s  %s%s', item_id, guid, loc_desc)
        converted_guids.append(guid)

    return converted_guids, n_skip, 0


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
    ap.add_argument('--maint-wait', type=int, default=3000, metavar='SECS',
                    help='Seconds to sleep when consecutive failures suggest a maintenance '
                         'window (default: 3000 = 50 min). Set 0 to disable.')
    ap.add_argument('--maint-threshold', type=int, default=3, metavar='N',
                    help='Consecutive item errors before sleeping (default: 3)')
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

    if loc and loc_type and loc_type not in LOC_PROP:
        sys.exit(
            f"ERROR: loc_type={loc_type!r} has no mapped property in LOC_PROP. "
            f"Add a property mapping before running this basis to avoid losing locator data."
        )

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

    # ---- Connect ----
    try:
        wbm = WBManager()
        wbi = wbm.get_wbi()
    except Exception as e:
        if args.dry_run:
            log.info('WBManager unavailable (%s).', e)
            log.info('Shallow dry-run (no credentials) — SPARQL item counts only.')
            for v in find_raw_variants(args.basis):
                v_items = find_items(v, args.item)
                log.info('  %r: %d item(s)', v, len(v_items))
            return
        sys.exit(f'ERROR: Cannot connect to FactGrid: {e}')

    # ---- Process items ----
    total_converted = total_skipped = total_errors = 0
    converted_guid_variant = {}   # guid -> basis_variant (for spot-check)

    def _process_list(item_list, basis_variant):
        """Process a list of items for one basis variant; return failed item_ids."""
        nonlocal total_converted, total_skipped, total_errors, converted_guid_variant
        failed = []
        consecutive = 0

        for item_id in item_list:
            if args.max_statements is not None and total_converted >= args.max_statements:
                log.info('Reached --max-statements %d — stopping early.', args.max_statements)
                break

            log.info('--- %s ---', item_id)
            try:
                guids, skipped, errors = process_item(
                    wbi, item_id, basis_variant, ref_qid, loc, loc_type,
                    done_guids, args.dry_run, args.delay, args.progress_log,
                    canonical_basis=args.basis,
                )
            except Exception as e:
                log.error('%s: unexpected error (retry exhaustion?): %s', item_id, e)
                guids, skipped, errors = [], 0, 1
            total_converted += len(guids)
            total_skipped   += skipped
            total_errors    += errors

            if guids:
                for g in guids:
                    converted_guid_variant[g] = basis_variant
                done_guids.update(guids)

            if errors and not guids:
                consecutive += 1
                failed.append(item_id)
                if (args.maint_wait > 0
                        and args.maint_threshold > 0
                        and consecutive >= args.maint_threshold):
                    log.warning(
                        '%d consecutive item failures — possible FactGrid maintenance '
                        'window. Sleeping %ds before continuing.',
                        consecutive, args.maint_wait,
                    )
                    time.sleep(args.maint_wait)
                    log.info('Resuming after sleep.')
                    consecutive = 0
            else:
                consecutive = 0

        return failed

    # ---- Discover HTML variants and process each ----
    variants = find_raw_variants(args.basis)
    if len(variants) > 1:
        extras = [v for v in variants if v != args.basis]
        log.info('HTML variants: %s', ', '.join(repr(v) for v in extras))

    variant_retries = {}   # variant -> [item_ids]
    for variant in variants:
        v_items = find_items(variant, args.item)
        if not v_items:
            if variant != args.basis:
                log.info('Variant %r: 0 items, skipping', variant)
            continue
        if variant != args.basis:
            log.info('Variant %r: %d item(s)', variant, len(v_items))
        failed = _process_list(v_items, variant)
        if failed:
            variant_retries[variant] = failed

    # ---- Retry failed items ----
    if variant_retries and not args.dry_run:
        total_retry = sum(len(v) for v in variant_retries.values())
        log.info('')
        log.info('Retrying %d item(s)...', total_retry)
        done_guids = load_done_guids(args.progress_log)
        for variant, retry_items in variant_retries.items():
            still_failed = _process_list(retry_items, variant)
            if still_failed:
                log.warning('%d item(s) still failing for %r: %s',
                            len(still_failed), variant, ', '.join(still_failed))

    # ---- Summary ----
    log.info('')
    log.info('=== Run complete ===')
    log.info('Converted : %d statement(s)', total_converted)
    log.info('Skipped   : %d (already done)', total_skipped)
    log.info('Errors    : %d', total_errors)
    if total_errors:
        log.warning('There were errors — review the log above before continuing.')

    # ---- Spot-check ----
    if not args.dry_run and converted_guid_variant:
        all_guids = list(converted_guid_variant)
        sample = (all_guids if len(all_guids) <= SPOT_CHECK_LIMIT
                  else random.sample(all_guids, SPOT_CHECK_LIMIT))
        log.info('')
        log.info('API spot-check on %d/%d GUID(s)...', len(sample), len(all_guids))
        # Group sample by variant so each api_spot_check call uses the right P721 string.
        by_variant = {}
        for guid in sample:
            v = converted_guid_variant[guid]
            by_variant.setdefault(v, []).append(guid)
        ok = fail = errs = 0
        for variant, guids in by_variant.items():
            o, f, e = api_spot_check(guids, variant, ref_qid)
            ok += o; fail += f; errs += e
        log.info('Spot-check: %d OK, %d FAILED, %d errors', ok, fail, errs)
        if fail or errs:
            log.warning(
                'Spot-check failures — investigate before running further batches.'
            )


if __name__ == '__main__':
    main()
