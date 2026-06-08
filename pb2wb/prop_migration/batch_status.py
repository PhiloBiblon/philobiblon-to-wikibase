#!/usr/bin/env python3
"""Quick status check for the running basis migration batch.

Usage:
  python prop_migration/batch_status.py           # status only
  python prop_migration/batch_status.py --restart # restart if not running
"""

import argparse
import json
import os
import re
import subprocess
import sys

BATCH_LOG     = 'prop_migration/batch.log'
PROGRESS_LOG  = 'prop_migration/basis_migration_progress.jsonl'
BATCH_SCRIPT  = 'prop_migration/run_basis_batch.py'
TSV_PATH      = 'prop_migration/P721-P129.tsv'
DEFAULT_ARGS  = ['--skip-locators', '--delay', '1']
_HTML_TAG_RE  = re.compile(r'<[^>]+>')


def check_process():
    result = subprocess.run(
        ['pgrep', '-fl', 'run_basis_batch'],
        capture_output=True, text=True,
    )
    lines = [l for l in result.stdout.strip().splitlines() if 'pgrep' not in l]
    return lines


def tail_log(path, n=10):
    if not os.path.exists(path):
        return '(log not found)'
    with open(path) as f:
        lines = f.readlines()
    return ''.join(lines[-n:]).rstrip()


def count_done():
    counts = {}
    last = None
    if not os.path.exists(PROGRESS_LOG):
        return counts, 0, None
    with open(PROGRESS_LOG) as f:
        for line in f:
            try:
                rec = json.loads(line)
                b = _HTML_TAG_RE.sub('', rec['basis']).strip()
                counts[b] = counts.get(b, 0) + 1
                last = rec
            except Exception:
                pass
    return counts, sum(counts.values()), last


def lookup_tsv_row(basis):
    """Return first TSV row whose basis column matches (case-insensitive strip)."""
    if not os.path.exists(TSV_PATH):
        return None
    target = basis.strip().lower()
    with open(TSV_PATH, encoding='utf-8') as f:
        header = f.readline().rstrip('\n').split('\t')
        for line in f:
            parts = line.rstrip('\n').split('\t')
            if len(parts) >= 2 and parts[1].strip().lower() == target:
                return dict(zip(header, parts))
    return None


def restart():
    cmd = ['caffeinate', '-is', sys.executable, BATCH_SCRIPT] + DEFAULT_ARGS
    proc = subprocess.Popen(
        cmd,
        stdout=open(BATCH_LOG, 'a'),
        stderr=subprocess.STDOUT,
    )
    print(f'RESTART: launched PID {proc.pid}')
    print(f'  cmd: {" ".join(cmd)} >> {BATCH_LOG}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--restart', action='store_true',
                    help='Restart the batch runner if it is not running')
    args = ap.parse_args()

    procs = check_process()
    if procs:
        print('PROCESS: running')
        for p in procs:
            print(' ', p)
    else:
        print('PROCESS: *** NOT RUNNING ***')
        if args.restart:
            restart()

    print()
    counts, total, last = count_done()
    print(f'PROGRESS: {len(counts)} bases done, {total:,} total GUIDs')

    if last:
        basis = _HTML_TAG_RE.sub('', last['basis']).strip()
        qid_count = counts.get(basis, 0)
        print(f'LAST ENTRY: item={last["item"]}  basis={basis!r}  ref_qid={last["qid"]}  '
              f'GUIDs for this basis so far: {qid_count:,}  ts={last["ts"][:19]}')
        row = lookup_tsv_row(basis)
        if row:
            freq   = row.get('F', '?')
            label  = row.get('label', '?')
            vetted = row.get('vetted', '?')
            loc    = row.get('loc', '')
            lt     = row.get('loc_type', '')
            loc_str = f'  loc={loc!r} ({lt})' if loc else ''
            print(f'  TSV: freq={freq}  label={label!r}  vetted={vetted}{loc_str}')
        else:
            print(f'  TSV: no matching row for {basis!r}')

    print()
    print('LAST 10 LOG LINES:')
    print(tail_log(BATCH_LOG, 10))


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    main()
