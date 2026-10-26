#!/usr/bin/env python3
"""
run_basis_batch.py — Batch runner for apply_basis_migration.py

Reads P721-P129.tsv, selects vetted=Y rows sorted by descending frequency,
and converts each basis in turn with apply_basis_migration.run_basis(), in
this process: one FactGrid login (and one API ping) for the whole run, not
one per basis. Progress is inferred from the JSONL log.

  # Restrict to / leave out a list of bases (one per line, # comments allowed)
  python prop_migration/run_basis_batch.py --live-counts ... --include prop_migration/include_a1.txt
  python prop_migration/run_basis_batch.py --live-counts ... --exclude prop_migration/held_bases.tsv

Usage (from pb2wb/):
  # Preview what would run
  python prop_migration/run_basis_batch.py --min-freq 332 --dry-run

  # Run top-35 bases (50% coverage target)
  python prop_migration/run_basis_batch.py --min-freq 332

  # Next tier
  python prop_migration/run_basis_batch.py --min-freq 80 --max-freq 331

  # First N bases only (for testing)
  python prop_migration/run_basis_batch.py --min-freq 332 --limit 3

  # Plan from live FactGrid counts (recommended): export first, then run
  python prop_migration/fetch_basis_values.py --out prop_migration/P721-live.tsv
  python prop_migration/run_basis_batch.py --live-counts prop_migration/P721-live.tsv --dry-run

A per-run summary is appended to batch_run_log.jsonl after each basis.

Without --live-counts, the plan uses the sheet's frequency column (a June
snapshot): bases where done_guids >= sheet freq are skipped without a SPARQL
call, which can miss usages added since the snapshot.
With --live-counts, the plan uses how many P721 usages are actually still in
FactGrid per basis: bases absent from the export are done, and every other
vetted basis runs, however many GUIDs the progress log already records.
--min-freq / --max-freq then filter on the live remaining count.
Restart-safe: re-reads the progress log on each iteration.

On failure, the runner sleeps --maint-wait seconds (default 50 min) and
retries once. This covers the ~45-minute FactGrid daily maintenance window
(7pm ET). Disable with --maint-retries 0.
"""

import argparse
import csv
import json
import logging
import os
import re as _re
import sys
import time
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from common.sheet_fields import is_vetted, row_freq
from prop_migration.locators import LOC_PROP

_HTML_TAG_RE = _re.compile(r'<[^>]+>')

CANDIDATES_TSV       = 'prop_migration/P721-P129.tsv'
PROGRESS_LOG         = 'prop_migration/basis_migration_progress.jsonl'
BATCH_LOG            = 'prop_migration/batch_run_log.jsonl'
DEFAULT_DELAY        = 2.0
DEFAULT_MAINT_WAIT   = 3000   # 50 min — covers the ~45 min FG daily window (7pm ET)
DEFAULT_MAINT_RETRY  = 1      # retry once after sleeping

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger(__name__)


def load_done_counts(path):
    """Return Counter of basis -> GUIDs converted so far.

    Strips HTML tags from the basis field so that '<i>IGM</i>' and 'IGM'
    are counted together (matching the stripped form used in the TSV).
    """
    counts = Counter()
    if not os.path.exists(path):
        return counts
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                basis = _HTML_TAG_RE.sub('', json.loads(line)['basis']).strip()
                counts[basis] += 1
            except (json.JSONDecodeError, KeyError):
                pass
    return counts


def load_candidates(tsv_path, min_freq, max_freq, skip_locators=False, locators_only=False):
    """
    Return list of (freq, basis, qid, loc, loc_type) from tsv_path, vetted=Y,
    valid QID, within [min_freq, max_freq], deduplicated by basis (highest freq
    wins), sorted descending by freq.

    --skip-locators: exclude rows where loc is non-empty.
    --locators-only: include only rows where loc is non-empty.
    """
    seen = {}  # basis -> (freq, qid, loc, loc_type)
    with open(tsv_path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            if not is_vetted(row.get('vetted')):
                continue
            qid = row.get('qid', '').strip()
            if not qid or not qid.startswith('Q'):
                continue
            basis = row.get('basis', '').strip()
            if not basis:
                continue
            freq = row_freq(row)
            if min_freq is not None and freq < min_freq:
                continue
            if max_freq is not None and freq > max_freq:
                continue
            loc      = row.get('loc', '').strip()
            loc_type = row.get('loc_type', '').strip()
            if skip_locators and loc:
                continue
            if locators_only and not loc:
                continue
            if basis not in seen or freq > seen[basis][0]:
                seen[basis] = (freq, qid, loc, loc_type)
    rows = [(freq, basis, qid, loc, loc_type)
            for basis, (freq, qid, loc, loc_type) in seen.items()]
    rows.sort(key=lambda r: r[0], reverse=True)
    return rows


def load_live_counts(path):
    """
    Return Counter of basis -> P721 usages still in FactGrid, from a
    fetch_basis_values.py export (value, freq; .tsv or .csv).

    HTML variants ('<i>IGM</i>', 'IGM') are summed under the stripped form,
    matching the basis column of the sheet.
    """
    delim = ',' if path.endswith('.csv') else '\t'
    counts = Counter()
    with open(path, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f, delimiter=delim):
            basis = _HTML_TAG_RE.sub('', row.get('value', '')).strip()
            if basis:
                counts[basis] += row_freq(row)
    return counts


def apply_live_counts(candidates, live, min_freq=None, max_freq=None):
    """
    Replace each candidate's sheet freq with its live remaining count; drop
    bases with nothing left and apply the freq filters to the live count.
    """
    rows = []
    for _, basis, qid, loc, loc_type in candidates:
        n = live.get(basis, 0)
        if n == 0:
            continue
        if min_freq is not None and n < min_freq:
            continue
        if max_freq is not None and n > max_freq:
            continue
        rows.append((n, basis, qid, loc, loc_type))
    rows.sort(key=lambda r: r[0], reverse=True)
    return rows


def load_basis_list(path):
    """Bases from a file: one per line (first tab-separated field), # comments ignored."""
    bases = set()
    with open(path, encoding='utf-8') as f:
        for line in f:
            b = line.rstrip('\n').split('\t')[0].strip()
            if b and not b.startswith('#'):
                bases.add(b)
    return bases


def append_batch_log(path, basis, freq, returncode, converted, elapsed_s):
    rec = {
        'basis':      basis,
        'freq':       freq,
        'returncode': returncode,
        'converted':  converted,
        'elapsed_s':  round(elapsed_s, 1),
        'ts':         datetime.now(timezone.utc).isoformat(),
    }
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')


def load_fg_empty(batch_log_path, elapsed_threshold=10.0):
    """Return set of bases confirmed empty in FactGrid.

    A basis is 'FG-confirmed empty' if its most recent batch_run_log entry has
    returncode=0, converted=0, and elapsed_s < elapsed_threshold. The elapsed
    threshold distinguishes fast empty-SPARQL runs (~2-3s) from slow auth-expired
    runs where items were skipped without converting (which would take much longer).
    """
    if not os.path.exists(batch_log_path):
        return set()
    last_run = {}
    with open(batch_log_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                last_run[rec['basis']] = rec
            except (json.JSONDecodeError, KeyError):
                pass
    return {
        basis for basis, rec in last_run.items()
        if rec.get('returncode') == 0
        and rec.get('converted', 0) == 0
        and rec.get('elapsed_s', 999) < elapsed_threshold
    }


def main():
    ap = argparse.ArgumentParser(
        description='Batch runner for apply_basis_migration.py.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument('--min-freq', type=int, default=None, metavar='N',
                    help='Skip bases with TSV freq < N')
    ap.add_argument('--max-freq', type=int, default=None, metavar='N',
                    help='Skip bases with TSV freq > N')
    ap.add_argument('--limit', type=int, default=None, metavar='N',
                    help='Run only the first N bases (by descending freq)')
    ap.add_argument('--dry-run', action='store_true',
                    help='Show plan without calling apply_basis_migration.py')
    ap.add_argument('--delay', type=float, default=DEFAULT_DELAY, metavar='SECS',
                    help=f'Seconds between item writes (default: {DEFAULT_DELAY})')
    ap.add_argument('--max-statements', type=int, default=None, metavar='N',
                    help='Pass --max-statements N to each apply_basis_migration.py call')
    ap.add_argument('--maint-wait', type=int, default=DEFAULT_MAINT_WAIT, metavar='SECS',
                    help=f'Seconds to sleep after a failure before retrying (default: {DEFAULT_MAINT_WAIT})')
    ap.add_argument('--maint-retries', type=int, default=DEFAULT_MAINT_RETRY, metavar='N',
                    help=f'Times to retry a failed basis after sleeping (default: {DEFAULT_MAINT_RETRY}, 0=disable)')
    ap.add_argument('--skip-locators', action='store_true',
                    help='Skip bases that have a non-empty loc field (run no-locator bases only)')
    ap.add_argument('--locators-only', action='store_true',
                    help='Run only bases that have a non-empty loc field')
    ap.add_argument('--live-counts', metavar='PATH',
                    help='fetch_basis_values.py export of current P721 counts; plan from '
                         'what is still in FactGrid instead of the sheet freq')
    ap.add_argument('--include', metavar='FILE',
                    help='only run bases listed in FILE (one per line)')
    ap.add_argument('--exclude', metavar='FILE',
                    help='never run bases listed in FILE (one per line; tab-separated reason ok)')
    ap.add_argument('--tsv', default=CANDIDATES_TSV, metavar='PATH')
    ap.add_argument('--progress-log', default=PROGRESS_LOG, metavar='PATH')
    ap.add_argument('--batch-log', default=BATCH_LOG, metavar='PATH')
    args = ap.parse_args()

    live = None
    if args.live_counts:
        live = load_live_counts(args.live_counts)
        age_h = (time.time() - os.path.getmtime(args.live_counts)) / 3600
        log.info('Live counts: %s (%d bases, %d usages, %.1fh old)',
                 args.live_counts, len(live), sum(live.values()), age_h)
        if age_h > 24:
            log.warning('Live counts are more than a day old — consider re-exporting')

    candidates = load_candidates(args.tsv,
                                 None if live else args.min_freq,
                                 None if live else args.max_freq,
                                 skip_locators=args.skip_locators,
                                 locators_only=args.locators_only)
    n_vetted = len(candidates)
    done_counts = load_done_counts(args.progress_log)

    if live is not None:
        candidates = apply_live_counts(candidates, live, args.min_freq, args.max_freq)
        n_already_done = n_vetted - len(candidates)
    else:
        fg_empty = load_fg_empty(args.batch_log)
        candidates_todo = [(f, b, q, l, lt) for f, b, q, l, lt in candidates
                           if done_counts.get(b, 0) < f and b not in fg_empty]
        n_already_done = len(candidates) - len(candidates_todo)
        candidates = candidates_todo
    if args.include:
        keep = load_basis_list(args.include)
        n_before = len(candidates)
        candidates = [c for c in candidates if c[1] in keep]
        log.info('Include list %s: %d bases listed, %d of %d candidates kept',
                 args.include, len(keep), len(candidates), n_before)
    if args.exclude:
        drop = load_basis_list(args.exclude)
        n_before = len(candidates)
        candidates = [c for c in candidates if c[1] not in drop]
        log.info('Exclude list %s: %d candidates left out', args.exclude,
                 n_before - len(candidates))

    # A locator type with no property can't be written without losing the
    # locator, so leave those bases out.
    unmapped = Counter(lt or '(blank)' for _, _, _, l, lt in candidates
                       if l and lt not in LOC_PROP)
    if unmapped:
        candidates = [c for c in candidates if not c[3] or c[4] in LOC_PROP]
        log.warning('Skipping %d bases whose locator type has no property: %s',
                    sum(unmapped.values()),
                    ', '.join(f'{t} ×{n}' for t, n in unmapped.most_common()))
    if args.limit:
        candidates = candidates[:args.limit]

    if not candidates:
        log.info('No candidates match the given filters — nothing to do.')
        return

    log.info('Batch plan: %d bases (%d already done or filtered out)',
             len(candidates), n_already_done)
    log.info('  plan from  : %s', 'live FactGrid counts' if live is not None else 'sheet freq')
    if args.min_freq:
        log.info('  min_freq   : %d', args.min_freq)
    if args.max_freq:
        log.info('  max_freq   : %d', args.max_freq)
    if args.skip_locators:
        log.info('  locators   : skipped')
    if args.locators_only:
        log.info('  locators   : only')
    if args.limit:
        log.info('  limit      : %d', args.limit)
    log.info('  mode       : %s', 'DRY RUN' if args.dry_run else 'EXECUTE')
    log.info('  delay      : %.1fs', args.delay)
    total_freq = sum(f for f, _, _, _, _ in candidates)
    log.info('  total freq : %d %s', total_freq,
             'usages remaining' if live is not None else 'statements')

    total_converted = 0
    total_errors = 0
    n_skipped_done = 0

    wbi = None
    if not args.dry_run:
        import prop_migration.apply_basis_migration as abm   # sets TEMP_WB=FACTGRID
        log.info('Pinging FactGrid API...')
        if not abm.ping_api():
            log.error('FactGrid API is not reachable — check for a maintenance window.')
            return
        wbi = abm.connect()      # one login for the whole run; re-login on expiry

    for i, (freq, basis, qid, loc, loc_type) in enumerate(candidates, 1):
        done = done_counts.get(basis, 0)
        prefix = f'[{i}/{len(candidates)}] freq={freq:,} {basis!r}'

        if live is None and done >= freq:
            log.info('%s — already done, skipping', prefix)
            n_skipped_done += 1
            continue

        remaining = freq if live is not None else freq - done
        if args.dry_run:
            log.info('[dry-run] %s → P129=%s  (%d remaining)', prefix, qid, remaining)
            continue

        if live is not None:
            log.info('%s → P129=%s  (%d remaining in FactGrid, %d converted earlier)',
                     prefix, qid, remaining, done)
        else:
            log.info('%s → P129=%s  (%d/%d done, %d remaining)',
                     prefix, qid, done, freq, remaining)
        log.info('─' * 60)

        basis_failed = False
        for attempt in range(args.maint_retries + 1):
            if attempt > 0:
                log.warning(
                    '%s — waiting %ds before retry %d/%d '
                    '(FactGrid maintenance window?)',
                    prefix, args.maint_wait, attempt, args.maint_retries,
                )
                time.sleep(args.maint_wait)
                log.info('%s — retrying...', prefix)

            t0 = time.monotonic()
            returncode = 0
            try:
                # Item-level errors are retried and reported inside run_basis (as the
                # old subprocess did with exit code 0); only an exception fails the basis.
                abm.run_basis(basis, wbi, max_statements=args.max_statements,
                              delay=args.delay, progress_log=args.progress_log, tsv=args.tsv)
            except abm.BasisConfigError as e:
                log.error('%s — not runnable: %s', prefix, e)
                append_batch_log(args.batch_log, basis, freq, 2, 0, time.monotonic() - t0)
                basis_failed = True
                break                       # a config problem won't fix itself by waiting
            except Exception as e:
                log.error('%s — unexpected error: %s', prefix, e)
                returncode = 1
            elapsed = time.monotonic() - t0

            new_done_counts = load_done_counts(args.progress_log)
            converted_this = new_done_counts.get(basis, 0) - done
            done_counts = new_done_counts

            append_batch_log(
                args.batch_log, basis, freq, returncode, converted_this, elapsed,
            )

            if returncode == 0:
                log.info('%s — done in %.1fs, +%d converted', prefix, elapsed, converted_this)
                total_converted += converted_this
                basis_failed = False
                break
            else:
                log.error('%s — FAILED (attempt %d/%d)',
                          prefix, attempt + 1, args.maint_retries + 1)
                total_converted += converted_this
                basis_failed = True

        if basis_failed:
            log.error('%s — giving up, moving to next basis', prefix)
            total_errors += 1

        log.info('─' * 60)

    log.info('')
    log.info('=== Batch complete ===')
    log.info('Bases run      : %d', len(candidates) - n_skipped_done)
    log.info('Already done   : %d', n_already_done + n_skipped_done)
    log.info('Converted      : %d', total_converted)
    log.info('Errors         : %d', total_errors)


if __name__ == '__main__':
    main()
