#!/usr/bin/env python3
"""
apply_basis_migration.py — Convert P721 string qualifiers to P129 item references.

Reads vetted rows from P721-P129.tsv. For each targeted basis string, finds all
FactGrid statements carrying pq:P721=<basis>, adds a P129=<qid> reference (with
optional locator), then removes the P721 qualifier.

--ref-prop P702 writes the reference as P702 "Based on" = <qid> instead of P129,
for physical evidence in the book (colophon, title page, seal stamp, ...).

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

  # Physical evidence: reference P702 "Based on" instead of P129
  python prop_migration/apply_basis_migration.py --basis "colofón" --ref-prop P702 --dry-run
"""

import argparse
import csv
import json
import logging
import os
import random
import re
import signal
import sys
import time
from datetime import datetime, timezone

import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from wikibaseintegrator.datatypes import Item as WBItem, MonolingualText, String as WBString
from wikibaseintegrator.models import Reference
import wikibaseintegrator.wbi_helpers as _wbi_helpers

# Reduce wbi's internal connection-error retry delay from 60s → 10s.
# The default 60s sleep fires on every RemoteDisconnected/ConnectionReset before
# wbi retries internally, adding 60s overhead per occurrence. 10s is enough for
# transient resets while keeping per-error cost manageable.
_d = list(_wbi_helpers.mediawiki_api_call.__defaults__)
_d[-1] = 10
_wbi_helpers.mediawiki_api_call.__defaults__ = tuple(_d)
_d = list(_wbi_helpers.mediawiki_api_call_helper.__defaults__)
_d[5] = 10
_wbi_helpers.mediawiki_api_call_helper.__defaults__ = tuple(_d)

from common.settings import TEMP_DICT
from common.sheet_fields import is_vetted
from common.factgrid_access import USER_AGENT
TEMP_DICT['TEMP_WB'] = 'FACTGRID'
from common.wb_manager import WBManager

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SPARQL_ENDPOINT = 'https://database.factgrid.de/sparql'
API_ENDPOINT    = 'https://database.factgrid.de/w/api.php'
P721            = 'P721'
P129            = 'P129'
P702            = 'P702'          # Based on (physical evidence in the book)
P1243           = 'P1243'         # Physical description (monolingual-text qualifier)
REF_PROPS       = (P129, P702)
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

from prop_migration.locators import LOC_PROP, locator_snaks, repair_loc

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


def log_progress(path, guid, item_id, basis, qid, loc, loc_type, prop='', main_value='',
                 ref_prop=P129, evidence=(), description=''):
    """Append one converted-statement record to the progress log (ref_prop only if not
    P129, evidence and description only if any)."""
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
    if ref_prop != P129:
        rec['ref_prop'] = ref_prop
    if evidence:
        rec['evidence'] = list(evidence)
    if description:
        rec['description'] = description
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')


# ---------------------------------------------------------------------------
# Candidate lookup
# ---------------------------------------------------------------------------

def parse_evidence(cell):
    """'Q418813, Q512065' → ('Q418813', 'Q512065'). Raises ValueError on anything else."""
    qids = tuple(q.strip() for q in (cell or '').split(',') if q.strip())
    bad = [q for q in qids if not re.fullmatch(r'Q\d+', q)]
    if bad:
        raise ValueError(f'evidence must be comma-separated QIDs, got {bad}')
    return qids


def load_candidate(basis_str, tsv_path):
    """
    Return the first vetted=Y row for basis_str from the candidates TSV,
    as dict {qid, loc, loc_type, evidence, description}. Returns None if not found or not vetted.
    evidence: QIDs from an optional 'evidence' column (comma-separated), written as
    P702 "Based on" in the same reference block. description: optional 'description'
    column, added to the statement as a P1243 "Physical description" qualifier.
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
            if not is_vetted(row.get('vetted')):
                continue
            qid = row.get('qid', '').strip()
            if not qid or not qid.startswith('Q'):
                continue
            matches.append({
                'qid':      qid,
                'loc':      repair_loc(row_basis, row.get('loc', '')),
                'loc_type': row.get('loc_type', '').strip(),
                'evidence': parse_evidence(row.get('evidence', '')),
                'description': (row.get('description') or '').strip(),
            })

    if not matches:
        return None
    if len(matches) > 1:
        log.warning(
            '%r has %d vetted rows (compound basis?). '
            'Using first: qid=%s. Only one reference will be added.',
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


def _call_with_retry(fn, wbi=None):
    """
    Call fn() with a per-call timeout (CALL_TIMEOUT seconds). On timeout or
    requests.RequestException, retry with exponential backoff. Other exceptions
    propagate immediately.

    Pass wbi= to have the requests session closed on error, forcing a fresh
    TCP connection on retry instead of reusing a potentially stale pooled one.
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
            if wbi is not None:
                try:
                    wbi.session.close()
                except Exception:
                    pass
            if attempt < MAX_RETRIES - 1:
                log.warning(
                    'Call failed/timed out — retrying in %ds (attempt %d/%d): %s',
                    backoff, attempt + 1, MAX_RETRIES, e,
                )
                time.sleep(backoff)
                backoff = min(backoff * 2, 300)
            else:
                raise


# Set by main() to WBManager.relogin, so writes can recover from an expired session.
_relogin = None


def _is_auth_error(e):
    s = str(e)
    return 'no longer logged in' in s or 'anonymous token' in s


def _write_item(item, wbi):
    """
    item.write() with network retries; if the bot session has expired, log in
    again and retry the write once instead of skipping the item.
    """
    try:
        return _call_with_retry(lambda: item.write(), wbi=wbi)
    except Exception as e:
        if not _is_auth_error(e) or _relogin is None:
            raise
        log.warning('Auth session expired — logging in again and retrying: %s', e)
        login = _relogin()
        return _call_with_retry(lambda: item.write(login=login), wbi=wbi)


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
                headers={'User-Agent': USER_AGENT},
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


SPOT_CHECK_LIMIT = 3    # per basis: check all GUIDs if ≤ this many, else sample (each is a FactGrid read)


def api_spot_check(guids, basis_str, ref_qid, ref_prop=P129):
    """
    API-based GUID-level spot-check (no SPARQL propagation lag).

    Checks all GUIDs when ≤ SPOT_CHECK_LIMIT converted this run, otherwise
    samples SPOT_CHECK_LIMIT at random. For each GUID, fetches the statement
    via wbgetclaims and verifies:
      - pr:<ref_prop> = ref_qid is present in references
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
                headers={'User-Agent': USER_AGENT},
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

            has_ref = any(
                isinstance(snak.get('datavalue', {}).get('value'), dict)
                and snak['datavalue']['value'].get('id') == ref_qid
                for ref in stmt.get('references', [])
                for snak in ref.get('snaks', {}).get(ref_prop, [])
            )
            has_p721 = any(
                snak.get('datavalue', {}).get('value') == basis_str
                for snak in stmt.get('qualifiers', {}).get(P721, [])
            )

            if has_ref and not has_p721:
                ok += 1
                log.info('  spot-check %s: OK', guid)
            else:
                reasons = []
                if not has_ref:
                    reasons.append(f'{ref_prop} missing')
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


# PhiloBiblon database → language of its cataloguing (from the item's "BETA manid 123"-style alias)
DB_LANG = {'BETA': 'es', 'BITECA': 'ca', 'BITAGAP': 'pt'}


def item_lang(aliases, default):
    """Language for an item from its PhiloBiblon alias (wbgetentities 'aliases' JSON), else default."""
    dbs = {a.get('value', '').split(' ')[0].upper()
           for vals in (aliases or {}).values() for a in vals}
    found = [DB_LANG[d] for d in DB_LANG if d in dbs]
    return found[0] if len(found) == 1 else default


def add_description(claim, text, lang):
    """Add P1243=text@lang as a qualifier on claim unless that text is already there."""
    for snak in claim.qualifiers.get(P1243) or []:
        dv = snak.datavalue
        val = dv.get('value', {}) if isinstance(dv, dict) else {}
        if isinstance(val, dict) and val.get('text') == text:
            return False
    claim.qualifiers.add(MonolingualText(text=text, language=lang, prop_nr=P1243))
    return True


def _ref_item_ids(ref, prop):
    ids = set()
    for snak in ref.snaks.get(prop) or []:
        dv  = snak.datavalue
        val = dv.get('value', {}) if isinstance(dv, dict) else {}
        if isinstance(val, dict) and val.get('id'):
            ids.add(val['id'])
    return ids


def _ref_present(claim, ref_qid, ref_prop=P129, evidence=()):
    """True if a reference on claim already contains ref_prop=ref_qid (and, when evidence
    is given, P702 for every evidence QID in that same reference)."""
    for ref in claim.references:
        if ref_qid in _ref_item_ids(ref, ref_prop) and set(evidence) <= _ref_item_ids(ref, P702):
            return True
    return False


# ---------------------------------------------------------------------------
# Item processing
# ---------------------------------------------------------------------------

def process_item(wbi, item_id, basis_str, ref_qid, loc, loc_type,
                 done_guids, dry_run, delay, progress_path,
                 canonical_basis=None, ref_prop=P129, evidence=(), description=''):
    """
    Convert all P721=basis_str qualifiers on item_id to ref_prop=ref_qid references
    (plus P702=<each evidence QID> in the same reference block). A description is added
    to each statement as a P1243 qualifier in the language of the item's PhiloBiblon
    database (BETA es, BITECA ca, BITAGAP pt; es if unknown), unless already there.

    Two-phase write:
      Phase 1 — add references (one item write)
      Phase 2 — remove P721 qualifiers (one item write)
    If Phase 1 fails, Phase 2 is not attempted.

    Returns (converted, skipped, errors).
    """
    loc_desc = (f'  loc={loc!r} ({loc_type} → '
                + ' + '.join(f'{p}={v!r}' for p, v in locator_snaks(loc, loc_type)) + ')') if loc else ''
    if evidence:
        loc_desc += '  ' + ' + '.join(f'{P702}={q}' for q in evidence)
    if description:
        loc_desc += f'  {P1243}={description!r}'

    # ---- Fetch item ----
    try:
        item = _call_with_retry(lambda: wbi.item.get(item_id), wbi=wbi)
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
        if _ref_present(claim, ref_qid, ref_prop, evidence):
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
            log.info('[dry-run] %s  %-36s prop=%-5s  → %s=%s%s',
                     item_id, guid, prop, ref_prop, ref_qid, loc_desc)
        return [guid for guid, _ in to_add], n_skip, 0

    # ---- Phase 1: add references ----
    for guid, claim in to_add:
        ref = Reference()
        ref.add(WBItem(value=ref_qid, prop_nr=ref_prop))
        for snak_prop, snak_value in locator_snaks(loc, loc_type):
            ref.add(WBString(value=snak_value, prop_nr=snak_prop))
        for ev_qid in evidence:
            ref.add(WBItem(value=ev_qid, prop_nr=P702))
        claim.references.add(ref)
        if description:
            add_description(claim, description, item_lang(item.get_json().get('aliases'), 'es'))

    try:
        time.sleep(delay)
        _write_item(item, wbi)
        log.info('%s: Phase 1 done — added %s ref to %d statement(s)', item_id, ref_prop, len(to_add))
    except Exception as e:
        err_str = str(e)
        if 'external client site' in err_str and 'did not provide page information' in err_str:
            # Stale sitelink on the item — permanent, not a maintenance window.
            log.warning('%s: skipping — permanent sitelink error (stale external link): %s',
                        item_id, e)
            return [], n_skip, 0
        if _is_auth_error(e):
            # Session expired and re-login didn't help — transient auth failure, not a
            # maintenance window. The P721 is still there, so the next run picks it up.
            log.warning('%s: skipping — auth session expired, will retry on restart: %s',
                        item_id, e)
            return [], n_skip, 0
        log.error('%s: Phase 1 write (add refs) failed: %s', item_id, e)
        return [], n_skip, len(to_add)

    # ---- Phase 2: remove P721 qualifiers ----
    # Process to_add + already (ref was pre-existing; qualifier may still be there).
    all_guids = [guid for guid, _ in to_add] + [guid for guid, _ in already]

    try:
        item = _call_with_retry(lambda: wbi.item.get(item_id), wbi=wbi)
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
        _write_item(item, wbi)
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
                     prop=prop, main_value=main_value, ref_prop=ref_prop, evidence=evidence,
                     description=description)
        log.info('CONVERTED  %s  %s%s', item_id, guid, loc_desc)
        converted_guids.append(guid)

    return converted_guids, n_skip, 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

class BasisConfigError(Exception):
    """A basis can't be run as configured (not vetted, no QID, unmapped locator)."""


def connect():
    """Log in once; return a WikibaseIntegrator ready for run_basis()."""
    global _relogin
    wbm = WBManager()
    _relogin = wbm.relogin
    return wbm.get_wbi()


def run_basis(basis, wbi, *, item=None, max_statements=None, dry_run=False,
              delay=DEFAULT_DELAY, maint_wait=3000, maint_threshold=3,
              progress_log=PROGRESS_LOG, tsv=CANDIDATES_TSV, ref_prop=P129):
    """
    Convert every P721=basis qualifier to a ref_prop (P129 or P702) reference, using an existing
    login (wbi). Returns dict(converted, skipped, errors). Raises
    BasisConfigError if the basis isn't runnable.
    """
    if ref_prop not in REF_PROPS:
        raise BasisConfigError(f'ref_prop must be one of {REF_PROPS}, not {ref_prop!r}')
    case = load_candidate(basis, tsv)
    if case is None:
        raise BasisConfigError(
            f"'{basis}' not found in {tsv} with vetted=Y and a valid QID. "
            f"Check: row exists, vetted='Y', qid starts with 'Q'.")
    ref_qid  = case['qid']
    loc      = case['loc']
    loc_type = case['loc_type']
    evidence = case.get('evidence', ())
    description = case.get('description', '')
    if evidence and ref_prop != P129:
        raise BasisConfigError('evidence (P702) can only accompany a P129 reference')
    if loc and loc_type and loc_type not in LOC_PROP:
        raise BasisConfigError(
            f"loc_type={loc_type!r} has no mapped property in LOC_PROP. "
            f"Add a property mapping before running this basis to avoid losing locator data.")

    log.info('Basis    : %r  →  %s=%s', basis, ref_prop, ref_qid)
    if loc:
        log.info('Locator  : %r  (%s  →  %s)', loc, loc_type,
                 ' + '.join(f'{p}={v!r}' for p, v in locator_snaks(loc, loc_type)))
    if evidence:
        log.info('Evidence : %s', ' + '.join(f'{P702}={q}' for q in evidence))
    if description:
        log.info('Descr.   : %s=%r', P1243, description)
    log.info('Mode     : %s', 'DRY RUN' if dry_run else 'EXECUTE')
    if item:
        log.info('Item     : %s  (single-item pilot)', item)
    if max_statements:
        log.info('Cap      : %d statements max', max_statements)

    done_guids = load_done_guids(progress_log)
    log.info('Progress : %d GUIDs already done', len(done_guids))

    total_converted = total_skipped = total_errors = 0
    converted_guid_variant = {}   # guid -> basis_variant (for spot-check)

    def _process_list(item_list, basis_variant):
        """Process a list of items for one basis variant; return failed item_ids."""
        nonlocal total_converted, total_skipped, total_errors
        failed = []
        consecutive = 0

        for item_id in item_list:
            if max_statements is not None and total_converted >= max_statements:
                log.info('Reached --max-statements %d — stopping early.', max_statements)
                break

            log.info('--- %s ---', item_id)
            try:
                guids, skipped, errors = process_item(
                    wbi, item_id, basis_variant, ref_qid, loc, loc_type,
                    done_guids, dry_run, delay, progress_log,
                    canonical_basis=basis, ref_prop=ref_prop, evidence=evidence,
                    description=description,
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
                if maint_wait > 0 and maint_threshold > 0 and consecutive >= maint_threshold:
                    log.warning(
                        '%d consecutive item failures — possible FactGrid maintenance '
                        'window. Sleeping %ds before continuing.', consecutive, maint_wait)
                    time.sleep(maint_wait)
                    log.info('Resuming after sleep.')
                    consecutive = 0
            else:
                consecutive = 0

        return failed

    # ---- Discover HTML variants and process each ----
    variants = find_raw_variants(basis)
    if len(variants) > 1:
        extras = [v for v in variants if v != basis]
        log.info('HTML variants: %s', ', '.join(repr(v) for v in extras))

    variant_retries = {}   # variant -> [item_ids]
    for variant in variants:
        v_items = find_items(variant, item)
        if not v_items:
            if variant != basis:
                log.info('Variant %r: 0 items, skipping', variant)
            continue
        if variant != basis:
            log.info('Variant %r: %d item(s)', variant, len(v_items))
        failed = _process_list(v_items, variant)
        if failed:
            variant_retries[variant] = failed

    # ---- Retry failed items ----
    if variant_retries and not dry_run:
        total_retry = sum(len(v) for v in variant_retries.values())
        log.info('')
        log.info('Retrying %d item(s)...', total_retry)
        done_guids = load_done_guids(progress_log)
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
    if not dry_run and converted_guid_variant:
        all_guids = list(converted_guid_variant)
        sample = (all_guids if len(all_guids) <= SPOT_CHECK_LIMIT
                  else random.sample(all_guids, SPOT_CHECK_LIMIT))
        log.info('')
        log.info('API spot-check on %d/%d GUID(s)...', len(sample), len(all_guids))
        # Group sample by variant so each api_spot_check call uses the right P721 string.
        by_variant = {}
        for guid in sample:
            by_variant.setdefault(converted_guid_variant[guid], []).append(guid)
        ok = fail = errs = 0
        for variant, guids in by_variant.items():
            o, f, e = api_spot_check(guids, variant, ref_qid, ref_prop)
            ok += o; fail += f; errs += e
        log.info('Spot-check: %d OK, %d FAILED, %d errors', ok, fail, errs)
        if fail or errs:
            log.warning('Spot-check failures — investigate before running further batches.')

    return {'converted': total_converted, 'skipped': total_skipped, 'errors': total_errors}


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
    ap.add_argument('--ref-prop', default=P129, choices=REF_PROPS,
                    help='reference property: P129 According to (default) or P702 Based on')
    args = ap.parse_args()

    # Validate the basis before contacting FactGrid.
    if load_candidate(args.basis, args.tsv) is None:
        sys.exit(f"ERROR: '{args.basis}' not found in {args.tsv} with vetted=Y and a valid QID.")

    if not args.dry_run:
        log.info('Pinging FactGrid API...')
        if not ping_api():
            sys.exit('ERROR: FactGrid API is not reachable. '
                     'Aborting — check for a maintenance window and retry later.')
        log.info('  reachable.')

    try:
        wbi = connect()
    except Exception as e:
        if args.dry_run:
            log.info('WBManager unavailable (%s).', e)
            log.info('Shallow dry-run (no credentials) — SPARQL item counts only.')
            for v in find_raw_variants(args.basis):
                log.info('  %r: %d item(s)', v, len(find_items(v, args.item)))
            return
        sys.exit(f'ERROR: Cannot connect to FactGrid: {e}')

    try:
        run_basis(args.basis, wbi, item=args.item, max_statements=args.max_statements,
                  dry_run=args.dry_run, delay=args.delay, maint_wait=args.maint_wait,
                  maint_threshold=args.maint_threshold, progress_log=args.progress_log,
                  tsv=args.tsv, ref_prop=args.ref_prop)
    except BasisConfigError as e:
        sys.exit(f'ERROR: {e}')


if __name__ == '__main__':
    main()
