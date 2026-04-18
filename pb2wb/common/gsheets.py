"""
gsheets.py — reusable Google Sheets sync for prop_migration workflows.

Authentication: service account JSON key file.

Required environment variables (put in .env, never commit):
    GSHEETS_CREDENTIALS_PATH  — path to service account JSON key file

Usage:
    from common.gsheets import SheetSync

    sync = SheetSync(credentials_path, sheet_id)

    # Download sheet → local TSV
    n = sync.pull(worksheet_name, output_tsv_path)

    # Upload local TSV → sheet (in-place cell updates + row inserts for compounds)
    stats = sync.push(worksheet_name, local_tsv_path,
                      key_cols=['item', '_Place_of_publication'],
                      write_cols=['P241 Qid', 'P241_values', 'auto_match', 'vetted'],
                      skip_col='vetted', skip_value='Y')
"""

import copy
import csv
import re
import time
from collections import defaultdict

import gspread
from tqdm import tqdm

# Max ranges per batch_update call (well within Sheets API quota).
_BATCH_SIZE = 200

# Proactive throttle: minimum seconds between consecutive API write calls.
# Google Sheets allows 60 write requests/minute; 1.1s gives comfortable margin.
_MIN_CALL_INTERVAL = 1.1
_last_call_time    = 0.0

# Retry parameters for 429 rate-limit errors (safety net on top of throttle).
_MAX_RETRIES     = 6
_INITIAL_BACKOFF = 2   # seconds; doubles each retry (2, 4, 8, 16, 32, 64)


def _display_value(cell):
    """
    Return the plain display text for a cell value.
    Strips HYPERLINK formulas: =HYPERLINK("url","text") → "text".
    Leaves plain strings untouched.
    """
    m = re.match(r'=HYPERLINK\([^,]+,\s*"([^"]+)"\)', cell, re.IGNORECASE)
    return m.group(1) if m else cell


def _col_letter(n):
    """Convert 1-based column number to A1 letter(s) (handles A–ZZ)."""
    result = ''
    while n:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


class SheetSync:
    """
    Thin wrapper around gspread for push/pull operations on a single spreadsheet.

    Designed to be reused across prop_migration workflows: instantiate once,
    call pull() or push() for each worksheet you need to sync.
    """

    def __init__(self, credentials_path, sheet_id):
        self._gc = gspread.service_account(filename=credentials_path)
        self._sheet_id = sheet_id

    def _ws(self, worksheet_name):
        return self._gc.open_by_key(self._sheet_id).worksheet(worksheet_name)

    # ------------------------------------------------------------------
    # pull
    # ------------------------------------------------------------------

    def pull(self, worksheet_name, output_path):
        """
        Read all rows from worksheet and write to a local TSV file.
        Returns the number of data rows written (excluding header).
        """
        ws = self._ws(worksheet_name)
        print('  Fetching sheet data...', end=' ', flush=True)
        rows = ws.get_all_values()
        print(f'{len(rows)} rows')
        if not rows:
            raise ValueError(f'Worksheet {worksheet_name!r} is empty')
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
            writer.writerows(rows)
        return len(rows) - 1

    # ------------------------------------------------------------------
    # push
    # ------------------------------------------------------------------

    def push(self, worksheet_name, local_tsv_path, key_cols, write_cols,
             skip_col=None, skip_value=None, dry_run=False):
        """
        Update sheet cells in place from a local TSV file.

        Rows whose compound key (key_cols) maps 1-to-1 are updated via
        batch cell writes.  Rows whose key appears multiple times in the
        local TSV (compound-split rows) are handled by updating the existing
        sheet row for the first part and inserting new rows for subsequent
        parts.  Inserts are processed bottom-to-top so row-number shifts
        don't invalidate earlier lookups.

        The sheet is read with value_render_option=FORMULA so that HYPERLINK
        formulas in columns like A are preserved verbatim in inserted rows.

        Parameters
        ----------
        key_cols   : column names that together uniquely identify a row.
                     Compared after stripping HYPERLINK formulas.
        write_cols : column names to update.  Missing columns are appended
                     to the sheet header automatically.
        skip_col   : column in the SHEET to check before writing.
        skip_value : rows where skip_col already equals this are left alone.
        dry_run    : print a summary without writing anything.

        Returns
        -------
        dict: updated, skipped, missing, inserted_rows, new_cols
        """
        ws = self._ws(worksheet_name)

        # Read sheet preserving formulas so inserts reproduce them exactly.
        sheet_rows = ws.get_all_values(value_render_option='FORMULA')
        if not sheet_rows:
            raise ValueError(f'Worksheet {worksheet_name!r} is empty')

        sheet_header = list(sheet_rows[0])

        # ---- Ensure all write_cols exist in sheet header ----
        new_cols = []
        for col in write_cols:
            if col not in sheet_header:
                sheet_header.append(col)
                new_cols.append(col)

        # ---- Column-name → 0-based index ----
        def idx(name):
            try:
                return sheet_header.index(name)
            except ValueError:
                raise ValueError(
                    f'Column {name!r} not found. Header: {sheet_header}'
                )

        key_indices   = [idx(c) for c in key_cols]
        write_indices = [idx(c) for c in write_cols]
        skip_idx      = idx(skip_col) if skip_col else None

        # ---- key → list of (1-based row number, padded row data) ----
        # A key may appear multiple times when a previous push already inserted
        # compound rows.  Storing all occurrences lets us detect that and skip
        # re-inserting.  Key comparison uses display values; stored data keeps
        # formulas so they are reproduced verbatim in any new inserted rows.
        key_to_rows = defaultdict(list)
        for i, row in enumerate(sheet_rows[1:], start=2):
            padded = row + [''] * max(0, len(sheet_header) - len(row))
            key = tuple(_display_value(padded[j]) for j in key_indices)
            key_to_rows[key].append((i, padded))

        # ---- Read local TSV ----
        with open(local_tsv_path, encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            local_rows = list(reader)
            local_fieldnames = reader.fieldnames or []

        for c in write_cols:
            if c not in local_fieldnames:
                raise ValueError(
                    f'write_col {c!r} not found in local TSV {local_tsv_path}'
                )

        # ---- Group local rows by key ----
        local_by_key = defaultdict(list)
        for local_row in local_rows:
            key = tuple(
                _display_value(local_row.get(c, '')) for c in key_cols
            )
            local_by_key[key].append(local_row)

        # ---- Classify: regular updates vs compound groups ----
        cell_updates    = []   # {'range': 'F5', 'values': [['...']]}
        compound_groups = []   # (sheet_entries, local_group)
        updated = skipped = missing = 0

        for key, local_group in local_by_key.items():
            if key not in key_to_rows:
                missing += len(local_group)
                continue

            sheet_entries = key_to_rows[key]   # list of (row_num, row_data)
            first_row_num, first_row_data = sheet_entries[0]

            # Skip check on the first sheet row for this key.
            if skip_idx is not None:
                current = (first_row_data[skip_idx]
                           if skip_idx < len(first_row_data) else '')
                if current == skip_value:
                    skipped += len(local_group)
                    continue

            if len(local_group) == 1:
                # Regular single-row update.
                for col_name, col_i in zip(write_cols, write_indices):
                    cell_ref = f'{_col_letter(col_i + 1)}{first_row_num}'
                    cell_updates.append({
                        'range': cell_ref,
                        'values': [[local_group[0].get(col_name, '')]],
                    })
                updated += 1
            else:
                compound_groups.append((sheet_entries, local_group))
                updated += len(local_group)

        # ---- Dry run ----
        n_to_insert = sum(
            max(0, len(lg) - len(se))
            for se, lg in compound_groups
        )
        if dry_run:
            n_regular = updated - sum(len(lg) for _, lg in compound_groups)
            print(f'[dry-run] regular updates:  {n_regular} rows '
                  f'({len(cell_updates)} cells)')
            print(f'[dry-run] compound groups:  {len(compound_groups)} '
                  f'({sum(len(lg) for _, lg in compound_groups)} parts, '
                  f'{n_to_insert} rows to insert, '
                  f'{sum(len(lg) for _, lg in compound_groups) - n_to_insert} already in sheet)')
            print(f'[dry-run] skipped (vetted=Y): {skipped}  not found: {missing}')
            if new_cols:
                print(f'[dry-run] new columns: {new_cols}')
            return {
                'updated': updated, 'skipped': skipped, 'missing': missing,
                'inserted_rows': n_to_insert, 'new_cols': new_cols,
            }

        # ---- Write new column headers if needed ----
        if new_cols:
            # Expand the grid before writing beyond the current column boundary.
            _api_call(ws.resize, rows=ws.row_count, cols=len(sheet_header))
            header_updates = [{
                'range': f'{_col_letter(sheet_header.index(c) + 1)}1',
                'values': [[c]],
            } for c in new_cols]
            _batch(ws, header_updates)
            print(f'Added new sheet columns: {new_cols}')

        # ---- Batch regular cell updates ----
        _batch(ws, cell_updates, desc='Updating cells')

        # ---- Compound groups: update existing rows + insert missing ones ----
        # Process bottom-to-top (by last existing row number) so that inserts
        # above don't shift the row numbers of groups below.
        inserted_rows = 0
        compound_groups.sort(key=lambda x: -x[0][-1][0])  # desc last row num

        for sheet_entries, local_group in tqdm(
            compound_groups, desc='Compounds', unit='group', leave=True, disable=not compound_groups
        ):
            n_sheet  = len(sheet_entries)
            n_local  = len(local_group)
            n_insert = max(0, n_local - n_sheet)

            # Update write_cols for each existing sheet row paired with its
            # corresponding local row.
            pair_updates = []
            for (row_num, _), local_row in zip(sheet_entries, local_group):
                for col_name, col_i in zip(write_cols, write_indices):
                    pair_updates.append({
                        'range': f'{_col_letter(col_i + 1)}{row_num}',
                        'values': [[local_row.get(col_name, '')]],
                    })
            _batch(ws, pair_updates, desc=None)

            if n_insert == 0:
                continue   # already fully expanded from a previous run

            # Build full row data for the extra local rows that need inserting.
            # Base each new row on the last existing sheet row so A–E formulas
            # (item QID hyperlink etc.) are reproduced correctly.
            last_row_num, last_row_data = sheet_entries[-1]
            insert_data = []
            for local_row in local_group[n_sheet:]:
                full_row = list(last_row_data) + [''] * max(
                    0, len(sheet_header) - len(last_row_data)
                )
                for col_name, col_i in zip(write_cols, write_indices):
                    while len(full_row) <= col_i:
                        full_row.append('')
                    full_row[col_i] = local_row.get(col_name, '')
                insert_data.append(full_row)

            _api_call(
                ws.insert_rows,
                insert_data,
                row=last_row_num + 1,
                value_input_option='USER_ENTERED',
                inherit_from_before=True,
            )
            inserted_rows += n_insert

        return {
            'updated': updated, 'skipped': skipped, 'missing': missing,
            'inserted_rows': inserted_rows, 'new_cols': new_cols,
        }


def _api_call(fn, *args, **kwargs):
    """Throttle then call a gspread API function, retrying on 429.

    gspread.Worksheet.batch_update mutates its input dicts in-place (it
    prepends the sheet name to each range string).  Deep-copying args before
    every attempt ensures retries receive clean, unmutated data.
    """
    global _last_call_time
    elapsed = time.time() - _last_call_time
    if elapsed < _MIN_CALL_INTERVAL:
        time.sleep(_MIN_CALL_INTERVAL - elapsed)

    # Snapshot args before any mutation so each retry starts from the same state.
    original_args = copy.deepcopy(args)

    backoff = _INITIAL_BACKOFF
    for attempt in range(_MAX_RETRIES):
        _last_call_time = time.time()
        try:
            return fn(*copy.deepcopy(original_args), **kwargs)
        except gspread.exceptions.APIError as e:
            status = getattr(getattr(e, 'response', None), 'status_code', None)
            if status == 429 and attempt < _MAX_RETRIES - 1:
                print(f'  Rate limit hit, retrying in {backoff}s '
                      f'(attempt {attempt + 1}/{_MAX_RETRIES})...')
                time.sleep(backoff)
                backoff = min(backoff * 2, 64)
            else:
                raise


def _batch(ws, updates, desc=None):
    """Send updates in chunks, retrying each chunk on 429."""
    chunks = range(0, len(updates), _BATCH_SIZE)
    bar = tqdm(chunks, desc=desc, unit='batch', leave=True) if desc else chunks
    for i in bar:
        _api_call(
            ws.batch_update,
            updates[i: i + _BATCH_SIZE],
            value_input_option='USER_ENTERED',
        )
