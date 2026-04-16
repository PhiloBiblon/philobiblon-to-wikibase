"""
sync_sheet.py — push/pull the P1141→P241 place mapping Google Sheet.

Usage (from pb2wb/):
    python prop_migration/sync_sheet.py pull
    python prop_migration/sync_sheet.py pull --worksheet "Sheet1"
    python prop_migration/sync_sheet.py push
    python prop_migration/sync_sheet.py push --dry-run

Pull  reads the Google Sheet and writes:
    prop_migration/P1141-P241.tsv   (safe default — doesn't overwrite Charles's file)

Push  reads prop_migration/sheet_updated.tsv and updates the sheet in place:
    - matches rows by (item QID, place string) compound key
    - only writes: P241 Qid, P241_values, auto_match, vetted
    - skips rows where vetted is already 'Y' (Charles has finalised them)

Required environment variables (add to .env, never commit):
    GSHEETS_CREDENTIALS_PATH  — path to service account JSON key file
    P1141_SHEET_ID            — Google Sheet ID (from the sheet URL)
"""

import argparse
import os
import sys

dir_path = os.path.dirname(os.path.realpath(__file__))
parent_dir_path = os.path.dirname(dir_path)
sys.path.append(parent_dir_path)

from common.gsheets import SheetSync

# ── Paths ──────────────────────────────────────────────────────────────────
PULL_TSV    = 'prop_migration/P1141-P241.tsv'       # pull writes here (safe default)
UPDATED_TSV = 'prop_migration/sheet_updated.tsv'    # push reads from here

# ── Default worksheet tab name ──────────────────────────────────────────────
DEFAULT_WORKSHEET = 'P1141-P241'

# ── Column configuration ────────────────────────────────────────────────────
KEY_COLS   = ['item', '_Place_of_publication']
WRITE_COLS = ['P241 Qid', 'P241_values', 'auto_match', 'vetted']
SKIP_COL   = 'vetted'
SKIP_VALUE = 'Y'


def _load_env():
    """Load KEY=VALUE pairs from .qs_env or .env into os.environ.
    Only sets values not already present (explicit env vars take precedence).
    """
    for fname in ('.qs_env', '.env'):
        if os.path.exists(fname):
            with open(fname) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        os.environ.setdefault(k.strip(), v.strip())
            return


def _sync():
    _load_env()
    creds = os.environ.get('GSHEETS_CREDENTIALS_PATH', '').strip()
    sheet_id = os.environ.get('P1141_SHEET_ID', '').strip()
    if not creds:
        sys.exit('Error: GSHEETS_CREDENTIALS_PATH environment variable not set')
    if not sheet_id:
        sys.exit('Error: P1141_SHEET_ID environment variable not set')
    if not os.path.exists(creds):
        sys.exit(f'Error: credentials file not found: {creds}')
    return SheetSync(creds, sheet_id)


def cmd_pull(args):
    sync = _sync()
    print(f'Reading sheet:    tab={args.worksheet!r}  sheet_id={os.environ.get("P1141_SHEET_ID", "?")}')
    n = sync.pull(args.worksheet, PULL_TSV)
    print(f'Writing TSV:      {PULL_TSV}  ({n} rows)')


def cmd_push(args):
    sync = _sync()
    print(f'Reading TSV:      {UPDATED_TSV}')
    print(f'Writing sheet:    tab={args.worksheet!r}  sheet_id={os.environ.get("P1141_SHEET_ID", "?")}')
    stats = sync.push(
        worksheet_name=args.worksheet,
        local_tsv_path=UPDATED_TSV,
        key_cols=KEY_COLS,
        write_cols=WRITE_COLS,
        skip_col=SKIP_COL,
        skip_value=SKIP_VALUE,
        dry_run=args.dry_run,
    )
    prefix = '[dry-run] ' if args.dry_run else ''
    print(f'{prefix}updated: {stats["updated"]}  '
          f'inserted rows: {stats["inserted_rows"]}  '
          f'skipped (vetted=Y): {stats["skipped"]}  '
          f'not found in sheet: {stats["missing"]}')
    if stats['new_cols']:
        print(f'{prefix}new columns added: {stats["new_cols"]}')


def main():
    parser = argparse.ArgumentParser(
        description='Sync P1141→P241 mapping with Google Sheets')
    sub = parser.add_subparsers(dest='command', required=True)

    pull_p = sub.add_parser('pull', help='Download sheet → local TSV')
    pull_p.add_argument('--worksheet', default=DEFAULT_WORKSHEET,
                        help=f'Tab name (default: {DEFAULT_WORKSHEET!r})')

    push_p = sub.add_parser('push', help='Upload sheet_updated.tsv → sheet')
    push_p.add_argument('--worksheet', default=DEFAULT_WORKSHEET,
                        help=f'Tab name (default: {DEFAULT_WORKSHEET!r})')
    push_p.add_argument('--dry-run', action='store_true',
                        help='Show what would change without writing')

    args = parser.parse_args()
    {'pull': cmd_pull, 'push': cmd_push}[args.command](args)


if __name__ == '__main__':
    main()
