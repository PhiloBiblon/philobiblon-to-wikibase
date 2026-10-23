"""Unit tests for run_basis_batch planning and prop_migration/locators.py (no network)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from prop_migration.locators import LOC_PROP, locator_snaks
from prop_migration.run_basis_batch import apply_live_counts, load_live_counts


def test_load_live_counts_tsv_sums_html_variants(tmp_path):
    p = tmp_path / 'live.tsv'
    p.write_text('value\tfreq\n<i>IGM</i>\t5\nIGM\t2\nZarco\t3\n', encoding='utf-8')
    assert load_live_counts(str(p)) == {'IGM': 7, 'Zarco': 3}


def test_load_live_counts_csv(tmp_path):
    p = tmp_path / 'live.csv'
    p.write_text('value,freq\nfol. mod.,1070\n"Riquer 1962:35",4\n', encoding='utf-8')
    assert load_live_counts(str(p)) == {'fol. mod.': 1070, 'Riquer 1962:35': 4}


CANDS = [
    (500, 'Big', 'Q1', '', ''),           # sheet freq is stale
    (40, 'Done', 'Q2', '', ''),           # not in FactGrid any more
    (10, 'Grew', 'Q3', '', ''),           # more usages now than the sheet says
    (3, 'Small', 'Q4', '12', 'page'),
]
LIVE = {'Big': 7, 'Grew': 25, 'Small': 3, 'Unvetted': 99}


def test_apply_live_counts_uses_live_numbers():
    assert apply_live_counts(CANDS, LIVE) == [
        (25, 'Grew', 'Q3', '', ''),
        (7, 'Big', 'Q1', '', ''),
        (3, 'Small', 'Q4', '12', 'page'),
    ]


def test_apply_live_counts_filters_on_live_freq():
    assert [b for _, b, *_ in apply_live_counts(CANDS, LIVE, min_freq=5, max_freq=10)] == ['Big']


@pytest.mark.parametrize('loc,loc_type,expected', [
    ('I:286', 'volume', [('P105', 'I'), ('P54', '286')]),
    ('II: 335', 'volume', [('P105', 'II'), ('P54', '335')]),
    ('V', 'volume', [('P105', 'V')]),
    ('26n', 'footnote', [('P54', '26n')]),
    ('3r', 'folio', [('P100', '3r')]),
    ('sello', 'annotation', []),
    ('', 'page', []),
])
def test_locator_snaks(loc, loc_type, expected):
    assert locator_snaks(loc, loc_type) == expected


def test_annotation_and_shelfmark_unmapped():
    assert 'annotation' not in LOC_PROP and 'shelfmark' not in LOC_PROP
