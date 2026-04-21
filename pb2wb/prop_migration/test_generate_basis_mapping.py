"""
Unit tests for generate_basis_mapping.py helper functions.

Run from pb2wb/:
    python -m pytest prop_migration/test_generate_basis_mapping.py -v
"""

from unittest.mock import MagicMock, patch

import pytest

import io
import textwrap

from prop_migration.generate_basis_mapping import (
    _fetch_bibid_qids,
    _pick_best_result,
    api_search_one,
    detect_loc_type,
    extract_qid,
    hyperlink,
    is_excluded,
    load_sheet,
    parse_loc_columns,
    preprocess,
    strip_html,
    vetted_value,
)


# ---------------------------------------------------------------------------
# strip_html
# ---------------------------------------------------------------------------

class TestStripHtml:
    def test_italic_tags(self):
        assert strip_html('<i>IGM</i>') == 'IGM'

    def test_nested_tags(self):
        assert strip_html('<b><i>text</i></b>') == 'text'

    def test_no_tags(self):
        assert strip_html('Faulhaber') == 'Faulhaber'

    def test_tag_with_whitespace(self):
        assert strip_html('<i>DHEE</i> 1875') == 'DHEE 1875'

    def test_empty(self):
        assert strip_html('') == ''


# ---------------------------------------------------------------------------
# is_excluded
# ---------------------------------------------------------------------------

class TestIsExcluded:
    def test_fol_mod(self):
        assert is_excluded('fol. mod.')

    def test_fol_ant(self):
        assert is_excluded('fol. ant.')

    def test_question_mark(self):
        assert is_excluded('?')

    def test_bracketed_question_mark(self):
        assert is_excluded('[?]')

    def test_princeps(self):
        assert is_excluded('princeps')

    def test_case_insensitive(self):
        assert is_excluded('FOL. MOD.')

    def test_leading_trailing_space(self):
        assert is_excluded('  fol. mod.  ')

    def test_catalan_fol_variant(self):
        assert is_excluded('fol. ant. en xifres romanes')

    def test_catalan_fol_variant_2(self):
        assert is_excluded('fol. moderna a llapis')

    def test_wikidata_excluded(self):
        assert is_excluded('Wikidata')

    def test_wikidata_case_variant(self):
        assert is_excluded('WIkidata')

    def test_wikidata_with_date(self):
        assert is_excluded('Wikidata (2012-)')

    def test_wikipedia_excluded(self):
        assert is_excluded('Wikipedia')

    def test_wikipedia_case_variant(self):
        assert is_excluded('WIkipedia')

    def test_wikipedia_with_lang(self):
        assert is_excluded('Wikipedia en español')

    def test_fichero_excluded(self):
        assert is_excluded('fichero')

    def test_fichero_compound(self):
        assert is_excluded('fichero de Palacio')

    def test_fichero_with_prefix(self):
        assert is_excluded('BNE fichero')

    def test_oskicat_excluded(self):
        assert is_excluded('OskiCat')

    def test_oskicat_case_variant(self):
        assert is_excluded('OskICat')

    def test_url_excluded(self):
        assert is_excluded('https://de.wikipedia.org/wiki/Ferdinand')

    def test_normal_ref_not_excluded(self):
        assert not is_excluded('Faulhaber')

    def test_igm_not_excluded(self):
        assert not is_excluded('IGM')

    def test_dhee_not_excluded(self):
        assert not is_excluded('DHEE 1875')

    def test_dbe_not_excluded(self):
        assert not is_excluded('DB~e')


# ---------------------------------------------------------------------------
# detect_loc_type
# ---------------------------------------------------------------------------

class TestDetectLocType:
    def test_empty(self):
        assert detect_loc_type('') == ''

    def test_plain_number_is_page(self):
        assert detect_loc_type('60') == 'page'

    def test_footnote(self):
        assert detect_loc_type('27n') == 'footnote'

    def test_footnote_single_digit(self):
        assert detect_loc_type('3n') == 'footnote'

    def test_folio_verso(self):
        assert detect_loc_type('93v') == 'folio'

    def test_folio_recto(self):
        assert detect_loc_type('3r') == 'folio'

    def test_folio_with_f_prefix(self):
        assert detect_loc_type('f. 93v') == 'folio'

    def test_folio_with_f_no_space(self):
        assert detect_loc_type('f.3r') == 'folio'

    def test_roman_vol_page_is_page(self):
        assert detect_loc_type('I:286') == 'page'

    def test_year_like_number_is_page(self):
        assert detect_loc_type('1875') == 'page'


# ---------------------------------------------------------------------------
# preprocess
# ---------------------------------------------------------------------------

class TestPreprocess:

    # --- HTML stripping ---

    def test_html_stripped_before_processing(self):
        r = preprocess('<i>IGM</i>')
        assert r['basis'] == 'IGM'

    def test_dhee_html_stripped(self):
        r = preprocess('<i>DHEE</i> 1875')
        assert r['key'] == 'DHEE'
        assert r['loc'] == '1875'

    # --- Excluded ---

    def test_excluded_fol_mod(self):
        r = preprocess('fol. mod.')
        assert r['preproc_type'] == 'excluded'

    def test_excluded_question_mark(self):
        r = preprocess('?')
        assert r['preproc_type'] == 'excluded'

    def test_excluded_html_wraps_excluded_value(self):
        r = preprocess('<i>fol. mod.</i>')
        assert r['preproc_type'] == 'excluded'

    # --- Compound ---

    def test_compound_slash_with_spaces(self):
        r = preprocess('IGM / Faulhaber')
        assert r['preproc_type'] == 'compound'

    def test_slash_without_spaces_not_compound(self):
        # "BNE MSS/7811" — shelfmark slash, no spaces; must NOT be flagged compound
        r = preprocess('BNE MSS/7811')
        assert r['preproc_type'] != 'compound'

    # --- DHEE pattern ---

    def test_dhee_page_number(self):
        r = preprocess('DHEE 1875')
        assert r['key'] == 'DHEE'
        assert r['loc'] == '1875'
        assert r['loc_type'] == 'page'
        assert r['parse_pattern'] == 'dhee'
        assert r['preproc_type'] == ''

    def test_dhee_case_insensitive(self):
        r = preprocess('dhee 42')
        assert r['key'] == 'DHEE'
        assert r['loc'] == '42'

    # --- Author + year:locator ---

    def test_auth_year_loc_page(self):
        r = preprocess('Beltrán 1997:60')
        assert r['key'] == 'Beltrán 1997'
        assert r['loc'] == '60'
        assert r['loc_type'] == 'page'
        assert r['parse_pattern'] == 'auth_year_loc'

    def test_auth_year_loc_footnote(self):
        r = preprocess('Beltrán 1997:27n')
        assert r['key'] == 'Beltrán 1997'
        assert r['loc'] == '27n'
        assert r['loc_type'] == 'footnote'

    def test_auth_year_loc_folio(self):
        r = preprocess('Smith 2003:93v')
        assert r['key'] == 'Smith 2003'
        assert r['loc'] == '93v'
        assert r['loc_type'] == 'folio'

    def test_auth_year_loc_multiword_author(self):
        r = preprocess('García López 1997:60')
        assert r['key'] == 'García López 1997'
        assert r['loc'] == '60'

    # --- Roman numeral volume + page ---

    def test_roman_vol(self):
        r = preprocess('Arteaga I:286')
        assert r['key'] == 'Arteaga'
        assert r['loc'] == 'I:286'
        assert r['loc_type'] == 'page'
        assert r['parse_pattern'] == 'roman_vol'

    def test_roman_vol_multidigit(self):
        r = preprocess('Author XIV:45')
        assert r['key'] == 'Author'
        assert r['loc'] == 'XIV:45'

    def test_roman_vol_not_matched_by_auth_year_loc(self):
        # "Arteaga I:286" has no 4-digit year before the colon — must not match
        # auth_year_loc and must fall through to roman_vol
        r = preprocess('Arteaga I:286')
        assert r['parse_pattern'] == 'roman_vol'

    # --- Author + 4-digit year ---

    def test_auth_year(self):
        r = preprocess('Hernández 2006')
        assert r['key'] == 'Hernández 2006'
        assert r['loc'] == ''
        assert r['loc_type'] == ''
        assert r['parse_pattern'] == 'auth_year'

    def test_auth_year_multiword(self):
        r = preprocess('García López 1999')
        assert r['key'] == 'García López 1999'
        assert r['parse_pattern'] == 'auth_year'

    def test_auth_year_range_hyphen(self):
        r = preprocess('Dutton 1990-91')
        assert r['key'] == 'Dutton 1990-91'
        assert r['loc'] == ''
        assert r['parse_pattern'] == 'auth_year'

    def test_auth_year_range_full(self):
        r = preprocess('Resende 1990-2003')
        assert r['parse_pattern'] == 'auth_year'

    def test_auth_year_parenthesized(self):
        r = preprocess('Faria (2021)')
        assert r['key'] == 'Faria (2021)'
        assert r['parse_pattern'] == 'auth_year'

    def test_auth_year_paren_range(self):
        r = preprocess('Moreno (1979-80)')
        assert r['key'] == 'Moreno (1979-80)'
        assert r['parse_pattern'] == 'auth_year'

    def test_auth_year_ongoing(self):
        r = preprocess('CORDE (1992-)')
        assert r['key'] == 'CORDE (1992-)'
        assert r['parse_pattern'] == 'auth_year'

    def test_auth_year_et_al_paren(self):
        r = preprocess('Gomes et al. (2021)')
        assert r['parse_pattern'] == 'auth_year'

    def test_wikidata_with_date_excluded_not_auth_year(self):
        r = preprocess('Wikidata (2012-)')
        assert r['preproc_type'] == 'excluded'

    def test_shelfmark_bne_mss(self):
        r = preprocess('BNE MSS/7811')
        assert r['key'] == 'BNE MSS/7811'
        assert r['loc'] == ''
        assert r['parse_pattern'] == 'shelfmark'

    def test_shelfmark_frankfurt(self):
        r = preprocess('Frankfurt a/M: UB, lat. oct. 231')
        assert r['parse_pattern'] == 'shelfmark'

    def test_shelfmark_rah(self):
        r = preprocess('RAH 9-28-3/5495')
        assert r['parse_pattern'] == 'shelfmark'

    def test_compound_not_shelfmark(self):
        r = preprocess('IGM / Faulhaber')
        assert r['preproc_type'] == 'compound'

    def test_five_digit_number_not_auth_year(self):
        # 5-digit number at end — must NOT match auth_year (\d{4}$ requires
        # exactly 4 digits at the end with no digit before them in that group)
        r = preprocess('Smith 12345')
        assert r['parse_pattern'] == 'raw'

    # --- Raw fallback ---

    def test_raw_simple_name(self):
        r = preprocess('Faulhaber')
        assert r['key'] == 'Faulhaber'
        assert r['loc'] == ''
        assert r['parse_pattern'] == 'raw'

    def test_raw_igm(self):
        r = preprocess('IGM')
        assert r['parse_pattern'] == 'raw'

    def test_raw_ambiguous(self):
        # "Rodríguez x" — roman numeral 'x' without colon; ambiguous
        r = preprocess('Rodríguez x')
        assert r['parse_pattern'] == 'raw'

    # --- Priority ordering ---

    def test_excluded_checked_on_whole_string(self):
        # is_excluded checks the full stripped string, not sub-components.
        # '? / something' is not in EXCLUDED_VALUES, so compound fires instead.
        r = preprocess('? / something')
        assert r['preproc_type'] == 'compound'

    def test_dhee_before_auth_year(self):
        # "DHEE 1997" could match auth_year but dhee fires first
        r = preprocess('DHEE 1997')
        assert r['parse_pattern'] == 'dhee'
        assert r['key'] == 'DHEE'

    def test_auth_year_loc_before_roman_vol(self):
        # "Smith 1997:60" — has 4-digit year before colon; auth_year_loc fires first
        r = preprocess('Smith 1997:60')
        assert r['parse_pattern'] == 'auth_year_loc'

    def test_auth_year_before_raw(self):
        # "Pérez 2001" — auth_year fires, not raw
        r = preprocess('Pérez 2001')
        assert r['parse_pattern'] == 'auth_year'


# ---------------------------------------------------------------------------
# parse_loc_columns
# ---------------------------------------------------------------------------

class TestParseLocColumns:
    def test_empty_loc(self):
        r = parse_loc_columns('', '')
        assert all(v == '' for v in r.values())

    def test_folio_verso(self):
        r = parse_loc_columns('93v', 'folio')
        assert r['col_folio'] == '93v'
        assert r['col_page'] == '' and r['col_volume'] == ''

    def test_folio_with_prefix(self):
        r = parse_loc_columns('f. 3r', 'folio')
        assert r['col_folio'] == 'f. 3r'

    def test_footnote(self):
        r = parse_loc_columns('27n', 'footnote')
        assert r['col_footnote'] == '27n'
        assert r['col_page'] == ''

    def test_plain_page(self):
        r = parse_loc_columns('60', 'page')
        assert r['col_page'] == '60'
        assert r['col_date'] == '' and r['col_volume'] == ''

    def test_page_range(self):
        r = parse_loc_columns('48-50', 'page')
        assert r['col_page'] == '48-50'

    def test_page_range_en_dash(self):
        r = parse_loc_columns('48–50', 'page')
        assert r['col_page'] == '48–50'

    def test_roman_vol_page(self):
        r = parse_loc_columns('I:286', 'page')
        assert r['col_volume'] == 'I'
        assert r['col_page'] == '286'

    def test_roman_vol_page_range(self):
        r = parse_loc_columns('XIV:45-50', 'page')
        assert r['col_volume'] == 'XIV'
        assert r['col_page'] == '45-50'

    def test_arabic_vol_page(self):
        r = parse_loc_columns('4:286', 'page')
        assert r['col_volume'] == '4'
        assert r['col_page'] == '286'

    def test_year_in_range(self):
        r = parse_loc_columns('2004', 'page')
        assert r['col_date'] == '2004'
        assert r['col_page'] == ''

    def test_dhee_year_loc_goes_to_page(self):
        r = parse_loc_columns('1875', 'page', parse_pattern='dhee')
        assert r['col_page'] == '1875'
        assert r['col_date'] == ''

    def test_year_lower_bound(self):
        r = parse_loc_columns('1500', 'page')
        assert r['col_date'] == '1500'

    def test_year_upper_bound(self):
        r = parse_loc_columns('2100', 'page')
        assert r['col_date'] == '2100'

    def test_year_below_range_is_page(self):
        r = parse_loc_columns('1499', 'page')
        assert r['col_page'] == '1499'
        assert r['col_date'] == ''

    def test_year_above_range_is_page(self):
        r = parse_loc_columns('2101', 'page')
        assert r['col_page'] == '2101'
        assert r['col_date'] == ''

    def test_free_text_is_literal(self):
        r = parse_loc_columns('fecha de bautismo', 'page')
        assert r['col_literal'] == 'fecha de bautismo'
        assert r['col_page'] == ''

    def test_unknown_loc_type_is_literal(self):
        r = parse_loc_columns('something', '')
        assert r['col_literal'] == 'something'


# ---------------------------------------------------------------------------
# _pick_best_result
# ---------------------------------------------------------------------------

def _r(qid, label, desc, match_type, match_text=None):
    """Build a minimal wbsearchentities result dict."""
    return {
        'id': qid,
        'label': label,
        'description': desc,
        'match': {'type': match_type, 'text': match_text or label},
    }


class TestPickBestResult:
    def test_empty_results(self):
        assert _pick_best_result([], 'Dutton') == ('', '', '', '')

    def test_single_exact_label(self):
        results = [_r('Q1', 'Dutton', 'scholar', 'label')]
        qid, _, _, subtype = _pick_best_result(results, 'Dutton')
        assert qid == 'Q1' and subtype == 'label'

    def test_prefers_ref_qid_over_person(self):
        # Q1 = person with exact label; Q2 = reference work (pre-confirmed via BIBID alias)
        person = _r('Q1', 'Dutton', 'Spanish philologist', 'label')
        ref    = _r('Q2', 'Dutton', 'reference work', 'label')
        qid, _, _, subtype = _pick_best_result([person, ref], 'Dutton', ref_qids={'Q2'})
        assert qid == 'Q2' and subtype == 'label'

    def test_prefers_ref_desc_over_person(self):
        # No BIBID alias confirmed, but Q2 has a reference-source description
        person = _r('Q1', 'Cappelli', 'Italian surname', 'label')
        ref    = _r('Q2', 'Cappelli', 'bibliography of medieval abbreviations', 'label')
        qid, _, _, _ = _pick_best_result([person, ref], 'Cappelli')
        assert qid == 'Q2'

    def test_ref_qid_beats_ref_desc(self):
        # Q1 has a reference description, Q2 is confirmed via BIBID alias — prefer Q2
        ref_desc  = _r('Q1', 'Schiff', 'bibliographic reference', 'label')
        ref_bibid = _r('Q2', 'Schiff', 'reference source', 'label')
        qid, _, _, _ = _pick_best_result([ref_desc, ref_bibid], 'Schiff', ref_qids={'Q2'})
        assert qid == 'Q2'

    def test_falls_back_to_first_exact_when_no_signals(self):
        # Two exact label matches, no BIBID alias, no ref description
        r1 = _r('Q10', 'Author', 'person', 'label')
        r2 = _r('Q11', 'Author', 'another person', 'label')
        qid, _, _, _ = _pick_best_result([r1, r2], 'Author')
        assert qid == 'Q10'

    def test_falls_back_to_fuzzy_when_no_exact(self):
        results = [_r('Q99', 'Something Else', '', 'label', match_text='Different')]
        qid, _, _, subtype = _pick_best_result(results, 'OriginalQuery')
        assert qid == 'Q99' and subtype == 'fuzzy'

    def test_ref_desc_keywords(self):
        for desc in ['reference work', 'bibliographic catalog', 'critical edition',
                     'scholarly publication', 'obra de referencia']:
            person = _r('Q1', 'X', 'person', 'label')
            ref    = _r('Q2', 'X', desc, 'label')
            qid, _, _, _ = _pick_best_result([person, ref], 'X')
            assert qid == 'Q2', f'failed for desc={desc!r}'

    def test_rejects_family_name(self):
        results = [_r('Q230953', 'Schiff', 'family name', 'label')]
        qid, _, _, _ = _pick_best_result(results, 'Schiff')
        assert qid == ''

    def test_rejects_surname(self):
        results = [_r('Q1', 'Dutton', 'English surname', 'label')]
        qid, _, _, _ = _pick_best_result(results, 'Dutton')
        assert qid == ''

    def test_rejects_given_name(self):
        results = [_r('Q1', 'Rosa', 'given name', 'label')]
        qid, _, _, _ = _pick_best_result(results, 'Rosa')
        assert qid == ''

    def test_rejection_does_not_block_ref_source_with_bibid(self):
        # A confirmed reference source wins even if another candidate is a family name
        family = _r('Q1', 'Schiff', 'family name', 'label')
        ref    = _r('Q2', 'Schiff', 'reference work', 'label')
        qid, _, _, _ = _pick_best_result([family, ref], 'Schiff', ref_qids={'Q2'})
        assert qid == 'Q2'

    def test_rejection_does_not_block_ref_desc_match(self):
        family = _r('Q1', 'Cappelli', 'family name', 'label')
        ref    = _r('Q2', 'Cappelli', 'bibliography of medieval abbreviations', 'label')
        qid, _, _, _ = _pick_best_result([family, ref], 'Cappelli')
        assert qid == 'Q2'


# ---------------------------------------------------------------------------
# api_search_one  (mocked HTTP)
# ---------------------------------------------------------------------------

class TestApiSearchOne:
    def _mock_response(self, search_results):
        """Build a mock requests.Response returning the given search list."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {'search': search_results}
        return mock_resp

    def test_exact_label_match(self):
        result = [{'id': 'Q123', 'label': 'Faulhaber', 'description': 'scholar',
                   'match': {'type': 'label', 'text': 'Faulhaber'}}]
        with patch('prop_migration.generate_basis_mapping._SESSION') as mock_sess:
            mock_sess.get.return_value = self._mock_response(result)
            qid, label, desc, subtype = api_search_one('Faulhaber')
        assert qid == 'Q123'
        assert subtype == 'label'

    def test_alias_match(self):
        result = [{'id': 'Q456', 'label': 'IGM', 'description': 'index',
                   'match': {'type': 'alias', 'text': 'IGM'}}]
        with patch('prop_migration.generate_basis_mapping._SESSION') as mock_sess:
            mock_sess.get.return_value = self._mock_response(result)
            qid, label, desc, subtype = api_search_one('IGM')
        assert subtype == 'alias'

    def test_fuzzy_match(self):
        result = [{'id': 'Q789', 'label': 'Different Label', 'description': '',
                   'match': {'type': 'label', 'text': 'Something Else'}}]
        with patch('prop_migration.generate_basis_mapping._SESSION') as mock_sess:
            mock_sess.get.return_value = self._mock_response(result)
            qid, label, desc, subtype = api_search_one('Original Query')
        assert subtype == 'fuzzy'
        assert qid == 'Q789'

    def test_no_results(self):
        with patch('prop_migration.generate_basis_mapping._SESSION') as mock_sess:
            mock_sess.get.return_value = self._mock_response([])
            qid, label, desc, subtype = api_search_one('nothing')
        assert qid == ''
        assert subtype == ''

    def test_diacritic_insensitive_label_match(self):
        # "Hernández" in query, "Hernandez" returned as label text — still exact
        result = [{'id': 'Q999', 'label': 'Hernandez 2006', 'description': '',
                   'match': {'type': 'label', 'text': 'Hernandez 2006'}}]
        with patch('prop_migration.generate_basis_mapping._SESSION') as mock_sess:
            mock_sess.get.return_value = self._mock_response(result)
            qid, label, desc, subtype = api_search_one('Hernández 2006')
        assert subtype == 'label'


# ---------------------------------------------------------------------------
# vetted_value
# ---------------------------------------------------------------------------

class TestVettedValue:
    def test_api_label_is_auto(self):
        assert vetted_value('api_label') == 'auto'

    def test_api_alias_is_auto(self):
        assert vetted_value('api_alias') == 'auto'

    def test_api_fuzzy_is_blank(self):
        assert vetted_value('api_fuzzy') == ''

    def test_none_is_blank(self):
        assert vetted_value('none') == ''

    def test_llm_pending_is_blank(self):
        assert vetted_value('llm_pending') == ''

    def test_excluded_is_blank(self):
        assert vetted_value('excluded') == ''

    def test_compound_is_blank(self):
        assert vetted_value('compound') == ''


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
# hyperlink
# ---------------------------------------------------------------------------

class TestHyperlink:
    def test_wraps_qid(self):
        result = hyperlink('Q123')
        assert 'Q123' in result
        assert result.startswith('=HYPERLINK(')
        assert 'database.factgrid.de' in result

    def test_empty_returns_empty(self):
        assert hyperlink('') == ''


# ---------------------------------------------------------------------------
# load_sheet
# ---------------------------------------------------------------------------

SHEET_HEADER        = 'freq\tbasis\tkey\tloc\tloc_type\tmatch_type\tqid\tlabel\n'
SHEET_HEADER_VETTED = 'freq\tbasis\tkey\tloc\tloc_type\tmatch_type\tqid\tlabel\tvetted\n'

_FG_URL = 'https://database.factgrid.de/wiki/Item:'


def _make_sheet(*rows, with_vetted=False):
    """Build a minimal P721 sheet TSV.
    rows: (basis, qid) or (basis, qid, vetted) or (basis, qid, vetted, match_type).
    match_type defaults to 'api_label' when qid present, 'llm_pending' when not.
    """
    header = SHEET_HEADER_VETTED if with_vetted else SHEET_HEADER
    lines = [header]
    for row in rows:
        basis      = row[0]
        qid        = row[1]
        vetted     = row[2] if len(row) > 2 else ''
        match_type = row[3] if len(row) > 3 else ('api_label' if qid else 'llm_pending')
        qid_cell   = f'=HYPERLINK("{_FG_URL}{qid}","{qid}")' if qid else ''
        if with_vetted:
            lines.append(f'10\t{basis}\t{basis}\t\t\t{match_type}\t{qid_cell}\t\t{vetted}\n')
        else:
            lines.append(f'10\t{basis}\t{basis}\t\t\t{match_type}\t{qid_cell}\t\n')
    return ''.join(lines)


class TestLoadSheet:
    def _load(self, tsv_text, refresh=False):
        f = io.StringIO(tsv_text)
        with patch('builtins.open', lambda path, **kw: f):
            return load_sheet('dummy.tsv', refresh=refresh)

    # --- vetted rows ---

    def test_vetted_Y_with_qid_is_vetted(self):
        tsv = _make_sheet(('Faulhaber', 'Q123', 'Y'), with_vetted=True)
        vetted, resolved, pending = self._load(tsv)
        assert len(vetted) == 1 and len(resolved) == 0 and len(pending) == 0

    def test_vetted_auto_with_qid_is_vetted(self):
        tsv = _make_sheet(('Faulhaber', 'Q123', 'auto'), with_vetted=True)
        vetted, resolved, pending = self._load(tsv)
        assert len(vetted) == 1

    def test_vetted_Y_without_qid_is_pending(self):
        # Charles marked Y but no QID — still needs LLM/re-search
        tsv = _make_sheet(('Unknown', '', 'Y'), with_vetted=True)
        vetted, resolved, pending = self._load(tsv)
        assert len(vetted) == 0
        assert len(pending) == 1

    # --- resolved rows (already searched, not yet vetted) ---

    def test_api_label_blank_vetted_is_resolved(self):
        tsv = _make_sheet(('Faulhaber', 'Q123', ''), with_vetted=True)
        vetted, resolved, pending = self._load(tsv)
        assert len(vetted) == 0
        assert len(resolved) == 1
        assert len(pending) == 0

    def test_none_match_type_is_resolved(self):
        tsv = _make_sheet(('Unknown', '', '', 'none'), with_vetted=True)
        vetted, resolved, pending = self._load(tsv)
        assert len(resolved) == 1 and len(pending) == 0

    def test_none_match_type_refresh_is_pending(self):
        tsv = _make_sheet(('Unknown', '', '', 'none'), with_vetted=True)
        vetted, resolved, pending = self._load(tsv, refresh=True)
        assert len(resolved) == 0 and len(pending) == 1

    def test_excluded_is_resolved(self):
        tsv = _make_sheet(('fol. mod.', '', '', 'excluded'), with_vetted=True)
        vetted, resolved, pending = self._load(tsv)
        assert len(resolved) == 1 and len(pending) == 0

    def test_compound_is_resolved(self):
        tsv = _make_sheet(('A / B', '', '', 'compound'), with_vetted=True)
        vetted, resolved, pending = self._load(tsv)
        assert len(resolved) == 1 and len(pending) == 0

    # --- pending rows ---

    def test_llm_pending_is_pending(self):
        tsv = _make_sheet(('Faulhaber', ''), with_vetted=True)
        vetted, resolved, pending = self._load(tsv)
        assert len(pending) == 1 and len(resolved) == 0

    def test_no_match_type_is_pending(self):
        # Row with no match_type column at all (very first bootstrap upload)
        lines = [SHEET_HEADER_VETTED.replace('match_type\t', ''),
                 '10\tFaulhaber\tFaulhaber\t\t\t\t\t\n']
        # Simplest: just check that empty match_type → pending
        tsv = _make_sheet(('Faulhaber', '', '', ''), with_vetted=True)
        vetted, resolved, pending = self._load(tsv)
        assert len(pending) == 1

    # --- mixed ---

    def test_mixed_rows(self):
        tsv = _make_sheet(
            ('Faulhaber', 'Q1', 'Y'),           # vetted
            ('IGM',       'Q2', 'auto'),         # vetted
            ('Norton',    'Q3', '', 'api_label'),# resolved (matched, not yet vetted)
            ('Unknown',   '',   '', 'none'),     # resolved (searched, no match)
            ('Pending',   '',   ''),             # pending (llm_pending)
            with_vetted=True,
        )
        vetted, resolved, pending = self._load(tsv)
        assert len(vetted)   == 2
        assert len(resolved) == 2
        assert len(pending)  == 1

    def test_pending_sorted_by_freq_desc(self):
        header = SHEET_HEADER_VETTED
        lines  = [header,
                  '5\tA\tA\t\t\tllm_pending\t\t\t\n',
                  '20\tB\tB\t\t\tllm_pending\t\t\t\n',
                  '1\tC\tC\t\t\tllm_pending\t\t\t\n']
        f = io.StringIO(''.join(lines))
        with patch('builtins.open', lambda path, **kw: f):
            _, _, pending = load_sheet('dummy.tsv')
        freqs = [int(r['freq']) for r in pending]
        assert freqs == sorted(freqs, reverse=True)
