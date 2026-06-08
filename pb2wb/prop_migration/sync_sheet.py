"""
sync_sheet.py — push/pull prop_migration Google Sheets.

Usage (from pb2wb/):
    python prop_migration/sync_sheet.py pull
    python prop_migration/sync_sheet.py push [--dry-run]
    python prop_migration/sync_sheet.py seed           # initial upload only

    All commands accept --pipeline {p1141,p721} (default: p1141)
    and --worksheet TAB to override the default tab name.

Pipeline defaults:

  p1141 (Place of publication):
    pull  → prop_migration/P1141-P241.tsv
    push  ← prop_migration/sheet_updated.tsv
    seed  ← (not used; sheet pre-exists)
    tab     P1141-P241
    key     item + _Place_of_publication
    write   P241 Qid, P241_values, auto_match, vetted

  p721 (Basis / reference qualifier):
    pull  → prop_migration/P721-P129.tsv
    push  ← prop_migration/basis_candidates.tsv
    seed  ← prop_migration/P721-P129-seed.tsv
    tab     P721-P129
    key     basis
    write   freq, key, match_type, qid, label, vetted, loc_type, loc

Required environment variables (add to .qs_env, never commit):
    GSHEETS_CREDENTIALS_PATH  — path to service account JSON key file
    P1141_SHEET_ID            — Google Sheet ID for P1141→P241
    P721_SHEET_ID             — Google Sheet ID for P721→P129
"""

import argparse
import csv
import io
import json
import os
import sys

dir_path = os.path.dirname(os.path.realpath(__file__))
parent_dir_path = os.path.dirname(dir_path)
sys.path.append(parent_dir_path)

from common.gsheets import SheetSync

# ── Pipeline configurations ─────────────────────────────────────────────────

_PIPELINES = {
    'p1141': {
        'sheet_id_env': 'P1141_SHEET_ID',
        'pull_tsv':     'prop_migration/P1141-P241.tsv',
        'push_tsv':     'prop_migration/sheet_updated.tsv',
        'seed_tsv':     None,
        'worksheet':    'P1141-P241',
        'key_cols':     ['item', '_Place_of_publication'],
        'write_cols':   ['P241 Qid', 'P241_values', 'auto_match', 'vetted'],
        'skip_col':     'vetted',
        'skip_value':   ['Y', 'y', 'check', 'seen'],
    },
    'p721': {
        'sheet_id_env': 'P721_SHEET_ID',
        'pull_tsv':     'prop_migration/P721-P129.tsv',
        'push_tsv':     'prop_migration/basis_candidates.tsv',
        'seed_tsv':     'prop_migration/P721-P129-seed.tsv',
        'worksheet':    'cleaned_beta_bio_bases',
        'key_cols':     ['basis'],
        'write_cols':   ['freq', 'key', 'match_type', 'qid', 'label', 'vetted', 'loc_type', 'loc'],
        'skip_col':     'vetted',
        'skip_value':   ['Y', 'y', 'check', 'seen'],
    },
}


def _load_env():
    for fname in ('.qs_env', '.env'):
        if os.path.exists(fname):
            with open(fname) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        os.environ.setdefault(k.strip(), v.strip())
            return


def _sync(cfg):
    _load_env()
    creds = os.environ.get('GSHEETS_CREDENTIALS_PATH', '').strip()
    sheet_id = os.environ.get(cfg['sheet_id_env'], '').strip()
    if not creds:
        sys.exit('Error: GSHEETS_CREDENTIALS_PATH environment variable not set')
    if not sheet_id:
        sys.exit(f'Error: {cfg["sheet_id_env"]} environment variable not set')
    if not os.path.exists(creds):
        sys.exit(f'Error: credentials file not found: {creds}')
    return SheetSync(creds, sheet_id), sheet_id


def cmd_pull(args, cfg):
    sync, sheet_id = _sync(cfg)
    tab = args.worksheet or cfg['worksheet']
    print(f'Reading sheet:    tab={tab!r}  sheet_id={sheet_id}')
    n = sync.pull(tab, cfg['pull_tsv'])
    print(f'Writing TSV:      {cfg["pull_tsv"]}  ({n} rows)')


def cmd_push(args, cfg):
    sync, sheet_id = _sync(cfg)
    tab = args.worksheet or cfg['worksheet']
    push_tsv = cfg['push_tsv']
    print(f'Reading TSV:      {push_tsv}')
    print(f'Writing sheet:    tab={tab!r}  sheet_id={sheet_id}')
    stats = sync.push(
        worksheet_name=tab,
        local_tsv_path=push_tsv,
        key_cols=cfg['key_cols'],
        write_cols=cfg['write_cols'],
        skip_col=cfg['skip_col'],
        skip_value=cfg['skip_value'],
        dry_run=args.dry_run,
    )
    prefix = '[dry-run] ' if args.dry_run else ''
    print(f'{prefix}updated: {stats["updated"]}  '
          f'inserted rows: {stats["inserted_rows"]}  '
          f'skipped (locked): {stats["skipped"]}  '
          f'not found in sheet: {stats["missing"]}')
    if stats['new_cols']:
        print(f'{prefix}new columns added: {stats["new_cols"]}')


def _load_done_bases(batch_log_path):
    """Return set of basis strings that completed successfully (returncode=0)."""
    done = set()
    if not os.path.exists(batch_log_path):
        return done
    with open(batch_log_path, encoding='utf-8') as f:
        for line in f:
            try:
                rec = json.loads(line)
                if rec.get('returncode') == 0:
                    done.add(rec['basis'])
            except Exception:
                pass
    return done


def _mark_done_local(done_bases, tsv_path):
    """Update the 'done' column in the local TSV in-place."""
    with open(tsv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    if 'done' not in fieldnames:
        fieldnames = list(fieldnames) + ['done']

    updated = 0
    for row in rows:
        if row.get('basis', '').strip() in done_bases:
            if row.get('done', '') != 'Y':
                row['done'] = 'Y'
                updated += 1

    with open(tsv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t',
                                extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

    return updated


def cmd_mark_done(args, cfg):
    batch_log = args.batch_log
    done_bases = _load_done_bases(batch_log)
    if not done_bases:
        print(f'No completed bases found in {batch_log}')
        return

    print(f'Completed bases found: {len(done_bases)}')

    if args.local:
        tsv_path = cfg['pull_tsv']
        with open(tsv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            rows = list(reader)
        would_update = [r['basis'] for r in rows
                        if r.get('basis', '').strip() in done_bases
                        and r.get('done', '') != 'Y']
        print(f'Rows to mark done: {len(would_update)}')
        for b in would_update:
            print(f'  {b}')
        if args.dry_run:
            return
        updated = _mark_done_local(done_bases, tsv_path)
        print(f'Updated {updated} rows in {tsv_path}')
        return

    # Build an in-memory TSV with basis + done columns
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter='\t')
    writer.writerow(['basis', 'done'])
    for basis in sorted(done_bases):
        writer.writerow([basis, 'Y'])
    buf.seek(0)

    # Write to a temp file for push()
    tmp_path = 'prop_migration/.done_tmp.tsv'
    with open(tmp_path, 'w', encoding='utf-8') as f:
        f.write(buf.getvalue())

    sync, sheet_id = _sync(cfg)
    tab = args.worksheet or cfg['worksheet']
    print(f'Updating sheet:   tab={tab!r}  sheet_id={sheet_id}')
    stats = sync.push(
        worksheet_name=tab,
        local_tsv_path=tmp_path,
        key_cols=['basis'],
        write_cols=['done'],
        skip_col=None,
        dry_run=args.dry_run,
    )
    os.unlink(tmp_path)

    prefix = '[dry-run] ' if args.dry_run else ''
    print(f'{prefix}updated: {stats["updated"]}  '
          f'not found in sheet: {stats["missing"]}')
    if stats.get('new_cols'):
        print(f'{prefix}new columns added: {stats["new_cols"]}')


def cmd_seed(args, cfg):
    seed_tsv = cfg['seed_tsv']
    if not seed_tsv:
        sys.exit(f'Error: seed is not configured for pipeline {args.pipeline!r}')
    if not os.path.exists(seed_tsv):
        sys.exit(f'Error: seed TSV not found: {seed_tsv}')
    sync, sheet_id = _sync(cfg)
    tab = args.worksheet or cfg['worksheet']
    print(f'Seeding sheet:    tab={tab!r}  sheet_id={sheet_id}')
    print(f'Reading TSV:      {seed_tsv}')
    n = sync.seed(tab, seed_tsv)
    print(f'Done: {n} data rows written to {tab!r}')


def main():
    parser = argparse.ArgumentParser(
        description='Sync prop_migration Google Sheets')
    parser.add_argument('--pipeline', choices=list(_PIPELINES), default='p1141',
                        help='Which migration pipeline (default: p1141)')
    sub = parser.add_subparsers(dest='command', required=True)

    pull_p = sub.add_parser('pull', help='Download sheet → local TSV')
    pull_p.add_argument('--worksheet', default=None,
                        help='Tab name (overrides pipeline default)')

    push_p = sub.add_parser('push', help='Upload candidates TSV → sheet (in-place update)')
    push_p.add_argument('--worksheet', default=None,
                        help='Tab name (overrides pipeline default)')
    push_p.add_argument('--dry-run', action='store_true',
                        help='Show what would change without writing')

    seed_p = sub.add_parser('seed', help='Initial full upload of seed TSV → sheet')
    seed_p.add_argument('--worksheet', default=None,
                        help='Tab name (overrides pipeline default)')

    done_p = sub.add_parser('mark-done',
                            help='Write done=Y for bases completed in batch log')
    done_p.add_argument('--worksheet', default=None,
                        help='Tab name (overrides pipeline default)')
    done_p.add_argument('--batch-log', default='prop_migration/batch_run_log.jsonl',
                        metavar='PATH', help='Batch run log (default: batch_run_log.jsonl)')
    done_p.add_argument('--local', action='store_true',
                        help='Update local TSV only (no sheet write)')
    done_p.add_argument('--dry-run', action='store_true',
                        help='Show what would change without writing')

    args = parser.parse_args()
    cfg = _PIPELINES[args.pipeline]
    {'pull': cmd_pull, 'push': cmd_push, 'seed': cmd_seed,
     'mark-done': cmd_mark_done}[args.command](args, cfg)


if __name__ == '__main__':
    main()
