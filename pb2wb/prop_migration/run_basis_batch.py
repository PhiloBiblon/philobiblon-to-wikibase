#!/usr/bin/env python3
"""
run_basis_batch.py — Batch runner for apply_basis_migration.py

Reads P721-P129.tsv, selects vetted=Y rows sorted by descending frequency,
and calls apply_basis_migration.py for each basis in turn. Output from each
run streams live to the terminal. Progress is inferred from the JSONL log.

Usage (from pb2wb/):
  # Preview what would run
  python prop_migration/run_basis_batch.py --min-freq 332 --dry-run

  # Run top-35 bases (50% coverage target)
  python prop_migration/run_basis_batch.py --min-freq 332

  # Next tier
  python prop_migration/run_basis_batch.py --min-freq 80 --max-freq 331

  # First N bases only (for testing)
  python prop_migration/run_basis_batch.py --min-freq 332 --limit 3

A per-run summary is appended to batch_run_log.jsonl after each basis.
Bases where done_guids >= tsv_freq are skipped without a SPARQL call.
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
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone

_HTML_TAG_RE = _re.compile(r'<[^>]+>')

CANDIDATES_TSV       = 'prop_migration/P721-P129.tsv'
PROGRESS_LOG         = 'prop_migration/basis_migration_progress.jsonl'
APPLY_SCRIPT         = 'prop_migration/apply_basis_migration.py'
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
            if row.get('vetted', '').strip() not in ('Y', 'y'):
                continue
            qid = row.get('qid', '').strip()
            if not qid or not qid.startswith('Q'):
                continue
            basis = row.get('basis', '').strip()
            if not basis:
                continue
            try:
                freq = int(row.get('F', '0') or 0)
            except ValueError:
                continue
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
    ap.add_argument('--tsv', default=CANDIDATES_TSV, metavar='PATH')
    ap.add_argument('--progress-log', default=PROGRESS_LOG, metavar='PATH')
    ap.add_argument('--batch-log', default=BATCH_LOG, metavar='PATH')
    args = ap.parse_args()

    candidates = load_candidates(args.tsv, args.min_freq, args.max_freq,
                                 skip_locators=args.skip_locators,
                                 locators_only=args.locators_only)
    if args.limit:
        candidates = candidates[:args.limit]

    if not candidates:
        log.info('No candidates match the given filters — nothing to do.')
        return

    done_counts = load_done_counts(args.progress_log)

    log.info('Batch plan: %d bases', len(candidates))
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
    log.info('  total freq : %d statements', total_freq)

    total_converted = 0
    total_errors = 0
    n_skipped_done = 0

    for i, (freq, basis, qid, loc, loc_type) in enumerate(candidates, 1):
        done = done_counts.get(basis, 0)
        prefix = f'[{i}/{len(candidates)}] freq={freq:,} {basis!r}'

        if done >= freq:
            log.info('%s — already done, skipping', prefix)
            n_skipped_done += 1
            continue

        remaining = freq - done
        if args.dry_run:
            log.info('[dry-run] %s → P129=%s  (%d remaining)', prefix, qid, remaining)
            continue

        log.info('%s → P129=%s  (%d/%d done, %d remaining)',
                 prefix, qid, done, freq, remaining)
        log.info('─' * 60)

        cmd = [
            sys.executable, APPLY_SCRIPT,
            '--basis', basis,
            '--delay', str(args.delay),
            '--progress-log', args.progress_log,
            '--tsv', args.tsv,
        ]
        if args.max_statements:
            cmd += ['--max-statements', str(args.max_statements)]

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
            result = subprocess.run(cmd)
            elapsed = time.monotonic() - t0

            new_done_counts = load_done_counts(args.progress_log)
            converted_this = new_done_counts.get(basis, 0) - done
            done_counts = new_done_counts

            append_batch_log(
                args.batch_log, basis, freq, result.returncode, converted_this, elapsed,
            )

            if result.returncode == 0:
                log.info('%s — done in %.1fs, +%d converted', prefix, elapsed, converted_this)
                total_converted += converted_this
                basis_failed = False
                break
            else:
                log.error('%s — FAILED (rc=%d, attempt %d/%d)',
                          prefix, result.returncode, attempt + 1, args.maint_retries + 1)
                total_converted += converted_this
                basis_failed = True

        if basis_failed:
            log.error('%s — giving up, moving to next basis', prefix)
            total_errors += 1

        log.info('─' * 60)

    log.info('')
    log.info('=== Batch complete ===')
    log.info('Bases run      : %d', len(candidates) - n_skipped_done)
    log.info('Already done   : %d', n_skipped_done)
    log.info('Converted      : %d', total_converted)
    log.info('Errors         : %d', total_errors)


if __name__ == '__main__':
    main()
