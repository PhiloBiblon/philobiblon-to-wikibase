"""Unit tests for sheet_status.compute_status (no network)."""

import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from prop_migration.sheet_status import (COL_CONVERTED, COL_EXAMPLE, COL_QID, COL_REMAINING,
                                         COL_STATUS, compute_status)


def _row(qid, vetted='Y', loc='', loc_type=''):
    return [{'qid': qid, 'vetted': vetted, 'loc': loc, 'loc_type': loc_type, 'label': ''}]


def _p(guid, basis, qid, item='Q1', ts='2026-06-08T00:00:00+00:00'):
    return {'guid': guid, 'item': item, 'prop': 'P5', 'basis': basis, 'qid': qid,
            'loc': '', 'ts': ts}


SHEET = {
    'Done':     _row('Q10'),
    'Partly':   _row('Q10'),
    'Fresh':    _row('Q10'),
    'Moved':    _row('Q20'),
    'Cleared':  _row('', vetted=''),
    'Fixed':    _row('Q20'),
    'Held':     _row('Q10'),
    'Unused':   _row('Q10'),
    'Today':    _row('Q10'),
}
PROGRESS = [
    _p('g1', 'Done', 'Q10'),
    _p('g2', 'Partly', 'Q10'),
    _p('g3', 'Moved', 'Q10'),
    _p('g4', 'Cleared', 'Q10'),
    _p('g5', 'Fixed', 'Q10'),
    _p('g6', '<i>Done</i>', 'Q10', item='Q2'),
    _p('g7', 'Today', 'Q10', ts='2026-10-23T14:00:00+00:00'),
]
CORRECTIONS = [{'guid': 'g5', 'status': 'corrected', 'new_qid': 'Q20'}]
LIVE = Counter({'Partly': 3, 'Fresh': 7, 'Held': 2, 'Today': 1})


def _status():
    return compute_status(PROGRESS, CORRECTIONS, LIVE, SHEET, {'Held': 'works vs people'},
                          live_ts='2026-10-23T13:54:00+00:00')


def test_statuses():
    s = {b: r[COL_STATUS] for b, r in _status().items()}
    assert s == {
        'Done': 'converted',
        'Partly': 'partly converted',
        'Fresh': 'not started',
        'Moved': 'needs correction (1)',
        'Cleared': 'needs review: converted, QID since cleared',
        'Fixed': 'corrected',
        'Held': 'held: works vs people',
        'Unused': '',
        'Today': 'converted',           # converted after the export: remaining drops to 0
    }


def test_columns():
    st = _status()
    assert st['Done'][COL_CONVERTED] == '2 (2026-06-08)'     # HTML variant counted too
    assert st['Fixed'][COL_QID] == 'Q20'                     # effective QID after correction
    assert st['Moved'][COL_QID] == 'Q10'
    assert st['Partly'][COL_REMAINING] == 3
    assert st['Today'][COL_REMAINING] == 0
    assert st['Unused'][COL_REMAINING] == ''
    assert st['Done'][COL_EXAMPLE].startswith('=HYPERLINK("https://database.factgrid.de/wiki/Item:Q1"')
    assert st['Fresh'][COL_EXAMPLE] == ''
