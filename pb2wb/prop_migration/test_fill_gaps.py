"""
Unit tests for fill_gaps.py helper functions.

Run from pb2wb/:
    python -m pytest prop_migration/test_fill_gaps.py -v
"""

import csv
import io
import json
import textwrap
from unittest.mock import patch

import pytest

from prop_migration.fill_gaps import (
    extract_qid,
    is_compound,
    is_multi_city_compound,
    load_sheet,
    normalize,
    part_candidates,
    resolve_parts,
    stripped_candidates,
)


# ---------------------------------------------------------------------------
# normalize
# ---------------------------------------------------------------------------

class TestNormalize:
    def test_lowercase(self):
        assert normalize('Paris') == 'paris'

    def test_strips_diacritics(self):
        assert normalize('Göttin gen') == 'gottin gen'
        assert normalize('São Paulo') == 'sao paulo'
        assert normalize('Zürich') == 'zurich'


# ---------------------------------------------------------------------------
# extract_qid
# ---------------------------------------------------------------------------

class TestExtractQid:
    def test_bare_qid(self):
        assert extract_qid('Q81970') == 'Q81970'

    def test_hyperlink_formula(self):
        assert extract_qid('=HYPERLINK("https://database.factgrid.de/wiki/Item:Q81970","Q81970")') == 'Q81970'

    def test_url(self):
        assert extract_qid('https://database.factgrid.de/wiki/Item:Q12345') == 'Q12345'

    def test_empty(self):
        assert extract_qid('') == ''

    def test_no_qid(self):
        assert extract_qid('some text') == ''


# ---------------------------------------------------------------------------
# is_compound
# ---------------------------------------------------------------------------

class TestIsCompound:
    def test_spaced_hyphen(self):
        assert is_compound('Madrid - Frankfurt')

    def test_en_dash(self):
        assert is_compound('Paris – Berlin')

    def test_slash(self):
        assert is_compound('London / Edinburgh')

    def test_ampersand(self):
        assert is_compound('Hamburg & Leipzig')

    def test_semicolon(self):
        assert is_compound('Vienna; Berlin')

    def test_simple_city(self):
        assert not is_compound('Madrid')

    def test_city_with_qualifier(self):
        assert not is_compound('Aldershot (Hampshire)')

    def test_city_with_state(self):
        assert not is_compound('Burlington, Vermont')

    def test_hyphenated_city(self):
        # Winston-Salem has no spaces around the hyphen
        assert not is_compound('Winston-Salem')


# ---------------------------------------------------------------------------
# is_multi_city_compound
# ---------------------------------------------------------------------------

class TestIsMultiCityCompound:
    def test_both_sides_have_parens(self):
        assert is_multi_city_compound('Aldershot (Hampshire) - Brookfield (Vermont)')

    def test_both_sides_have_commas(self):
        assert is_multi_city_compound('Farnham, Surrey - Burlington, Vermont')

    def test_only_right_has_qualifier(self):
        # "Winston - Salem, N.C." — qualifier only on right, not a multi-city compound
        assert not is_multi_city_compound('Winston - Salem, N.C.')

    def test_no_qualifiers(self):
        assert not is_multi_city_compound('Genève - Paris')

    def test_simple_city(self):
        assert not is_multi_city_compound('Madrid')


# ---------------------------------------------------------------------------
# stripped_candidates
# ---------------------------------------------------------------------------

class TestStrippedCandidates:
    def test_paren_qualifier_extracted_and_stripped(self):
        # For main-path search: both the extracted content AND stripped form are candidates
        candidates = stripped_candidates('Aldershot (Hampshire)')
        assert 'Hampshire' in candidates         # extracted
        assert 'Aldershot' in candidates         # stripped
        assert 'Aldershot (Hampshire)' in candidates

    def test_bracket_qualifier(self):
        candidates = stripped_candidates('Salem [Mass]')
        assert 'Mass' in candidates
        assert 'Salem' in candidates

    def test_comma_stripping(self):
        candidates = stripped_candidates('Burlington, Vermont')
        assert 'Burlington' in candidates

    def test_simple_city_unchanged(self):
        candidates = stripped_candidates('Paris')
        assert candidates == ['Paris']


# ---------------------------------------------------------------------------
# part_candidates  (compound-part search — no qualifier extraction)
# ---------------------------------------------------------------------------

class TestPartCandidates:
    def test_paren_stripped_not_extracted(self):
        candidates = part_candidates('Aldershot (Hampshire)')
        assert 'Aldershot' in candidates            # stripped ✓
        assert 'Hampshire' not in candidates        # NOT extracted ✓

    def test_bracket_stripped_not_extracted(self):
        candidates = part_candidates('Salem [Mass]')
        assert 'Salem' in candidates
        assert 'Mass' not in candidates

    def test_comma_form_adds_paren_form_before_bare(self):
        # "Burlington, Vermont" → try "Burlington (Vermont)" before bare "Burlington"
        # so a FactGrid alias like "Burlington (Vermont)" is found first.
        candidates = part_candidates('Burlington, Vermont')
        assert 'Burlington (Vermont)' in candidates
        assert 'Burlington' in candidates
        assert candidates.index('Burlington (Vermont)') < candidates.index('Burlington')
        assert 'Vermont' not in candidates   # qualifier not extracted standalone

    def test_full_string_always_first(self):
        candidates = part_candidates('Aldershot (Hampshire)')
        assert candidates[0] == 'Aldershot (Hampshire)'

    def test_simple_city_unchanged(self):
        assert part_candidates('Paris') == ['Paris']


# ---------------------------------------------------------------------------
# resolve_parts  (requires mocking api_search_one)
# ---------------------------------------------------------------------------

class TestResolveParts:
    def _api_side_effect(self, query):
        """Fake API: only knows Aldershot and Brookfield exactly."""
        mapping = {
            'Aldershot':            ('Q1879493', 'Aldershot',  'town in Hampshire', 'label'),
            'Brookfield':           ('Q1880825', 'Brookfield', 'town in Vermont',   'label'),
            'Brookfield (Vermont)': ('Q1880825', 'Brookfield', 'town in Vermont',   'label'),
        }
        return mapping.get(query, ('', '', '', ''))

    def test_both_parts_resolve_to_distinct_items(self):
        with patch('prop_migration.fill_gaps.api_search_one',
                   side_effect=self._api_side_effect):
            result = resolve_parts(['Aldershot (Hampshire)', 'Brookfield (Vermont)'])

        assert len(result) == 2
        aldershot = next(r for r in result if 'Aldershot' in r['part'])
        brookfield = next(r for r in result if 'Brookfield' in r['part'])
        assert aldershot['qid'] == 'Q1879493', 'Aldershot should map to Q1879493'
        assert brookfield['qid'] == 'Q1880825', 'Brookfield should map to Q1880825'
        assert aldershot['qid'] != brookfield['qid'], 'Parts must not share a QID'

    def test_fuzzy_match_rejected(self):
        """resolve_parts must not accept fuzzy hits — they cause cross-part collisions."""
        def api_fuzzy(query):
            # Returns Brookfield as a fuzzy match for everything
            return ('Q1880825', 'Brookfield', 'town in Vermont', 'fuzzy')

        with patch('prop_migration.fill_gaps.api_search_one', side_effect=api_fuzzy):
            result = resolve_parts(['Aldershot (Hampshire)', 'Brookfield (Vermont)'])

        for r in result:
            assert r['qid'] == '', f'Fuzzy match should be rejected, got {r}'

    def test_paren_form_used_before_bare_city(self):
        """
        "Burlington, Vermont" must not resolve to Burlington Iowa.
        The paren form "Burlington (Vermont)" is tried first; if FactGrid
        has it as an alias, the correct item is returned.
        """
        def api_paren_aware(query):
            if query == 'Burlington (Vermont)':
                return ('Q999', 'Burlington', 'city in Vermont, United States', 'alias')
            if query == 'Burlington':
                return ('Q239189', 'Burlington', 'city in Iowa, United States', 'label')
            return ('', '', '', '')

        with patch('prop_migration.fill_gaps.api_search_one',
                   side_effect=api_paren_aware):
            result = resolve_parts(['Burlington, Vermont'])

        assert result[0]['qid'] == 'Q999', \
            'Should match Vermont Burlington via paren alias, not Iowa Burlington'

    def test_unknown_part_stays_blank(self):
        with patch('prop_migration.fill_gaps.api_search_one', return_value=('', '', '', '')):
            result = resolve_parts(['UnknownCity (Somewhere)'])
        assert result[0]['qid'] == ''


# ---------------------------------------------------------------------------
# load_sheet  (uses tmp file)
# ---------------------------------------------------------------------------

SHEET_HEADER = 'item\tP1141\t_Place_of_publication\titem\tP241\tP241 Qid\tP241_values\tWikidata\n'

def _make_sheet(*rows):
    """Build a minimal sheet TSV string from (place_string, qid) pairs."""
    lines = [SHEET_HEADER]
    for place, qid in rows:
        hyperlink = f'=HYPERLINK("https://database.factgrid.de/wiki/Item:{qid}","{qid}")' if qid else ''
        lines.append(f'Q1\tP1141\t{place}\tQ1\tP241\t{hyperlink}\t\t\n')
    return ''.join(lines)


class TestLoadSheet:
    def _load(self, tsv_text):
        f = io.StringIO(tsv_text)
        # load_sheet opens a file by path; patch open for this module
        with patch('builtins.open', lambda path, **kw: f):
            return load_sheet('dummy.tsv')

    def test_simple_city_seeded(self):
        tsv = _make_sheet(('Madrid', 'Q1234'))
        strings, seeded = self._load(tsv)
        assert seeded.get('Madrid') == 'Q1234'

    def test_compound_present_in_strings(self):
        tsv = _make_sheet(('Aldershot (Hampshire) - Brookfield (Vermont)', 'Q1880825'))
        strings, seeded = self._load(tsv)
        string_vals = [s for s, _ in strings]
        assert 'Aldershot (Hampshire) - Brookfield (Vermont)' in string_vals

    def test_count_aggregated(self):
        tsv = _make_sheet(('Paris', 'Q5'), ('Paris', ''), ('Paris', ''))
        strings, _ = self._load(tsv)
        counts = dict(strings)
        assert counts['Paris'] == 3
