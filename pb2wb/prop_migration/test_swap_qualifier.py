"""Unit tests for swap_qualifier.py (no network)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from wikibaseintegrator.models import Claim

from prop_migration.swap_qualifier import (_snak_value, item_lang, load_bases, should_verify, swap_on_claim,
                                           verify_claim)


def _find_p721(claim, basis):
    for s in claim.qualifiers.get('P721') or []:
        if isinstance(s.datavalue, dict) and s.datavalue.get('value') == basis:
            return s
    return None


def _str(prop, v):
    return {'snaktype': 'value', 'property': prop, 'datatype': 'string',
            'datavalue': {'type': 'string', 'value': v}}


def _item(prop, q):
    return {'snaktype': 'value', 'property': prop, 'datatype': 'wikibase-item',
            'datavalue': {'type': 'wikibase-entityid',
                          'value': {'entity-type': 'item', 'numeric-id': int(q[1:]), 'id': q}}}


def _claim(quals):
    qd = {}
    for s in quals:
        qd.setdefault(s['property'], []).append(s)
    return Claim().from_json({
        'mainsnak': _str('P222', '1495'), 'type': 'statement', 'rank': 'normal',
        'id': 'Q1$ABC', 'qualifiers': qd, 'qualifiers-order': list(qd), 'references': []})


UNCERTAIN = {'prop': 'P155', 'item': 'Q160240', 'text': None, 'text_from_basis': False, 'lang': 'es'}
FOLIATION = {'prop': 'P1243', 'item': None, 'text': None, 'text_from_basis': True, 'lang': 'es'}


def _quals(claim):
    return {p: sorted(str(_snak_value(s)) for s in claim.qualifiers.get(p) or [])
            for p in ('P721', 'P155', 'P1243', 'P700')}


def test_uncertainty_swap():
    c = _claim([_str('P721', '?')])
    assert swap_on_claim(c, '?', UNCERTAIN, '?', _find_p721) == 'swapped'
    assert _quals(c) == {'P721': [], 'P155': ['Q160240'], 'P1243': [], 'P700': []}
    assert verify_claim(c, '?', UNCERTAIN, '?', _find_p721)


def test_existing_other_p155_kept_and_identical_not_duplicated():
    c = _claim([_str('P721', '[?]'), _item('P155', 'Q10'), _item('P155', 'Q160240')])
    assert swap_on_claim(c, '[?]', UNCERTAIN, '[?]', _find_p721) == 'swapped'
    assert _quals(c)['P155'] == ['Q10', 'Q160240']     # circa kept, Uncertain not duplicated
    assert _quals(c)['P721'] == []


def test_only_matching_p721_removed():
    c = _claim([_str('P721', '?'), _str('P721', 'Faulhaber')])
    swap_on_claim(c, '?', UNCERTAIN, '?', _find_p721)
    assert _quals(c)['P721'] == ['Faulhaber']


def test_no_p721():
    c = _claim([_item('P155', 'Q160240')])
    assert swap_on_claim(c, '?', UNCERTAIN, '?', _find_p721) == 'no_p721'


def test_foliation_text_from_basis_keeps_p700():
    c = _claim([_str('P721', 'fol. mod.'), _item('P700', 'Q453606')])
    assert swap_on_claim(c, 'fol. mod.', FOLIATION, 'fol. mod.', _find_p721) == 'swapped'
    assert _quals(c) == {'P721': [], 'P155': [], 'P1243': ["('fol. mod.', 'es')"], 'P700': ['Q453606']}
    assert verify_claim(c, 'fol. mod.', FOLIATION, 'fol. mod.', _find_p721)


def test_html_variant_uses_canonical_text():
    c = _claim([_str('P721', '<i>fol. mod.</i>')])
    swap_on_claim(c, '<i>fol. mod.</i>', FOLIATION, 'fol. mod.', _find_p721)
    assert _quals(c)['P1243'] == ["('fol. mod.', 'es')"]


def test_should_verify():
    assert [n for n in range(1, 21) if should_verify(n, 10)] == [1, 2, 3, 10, 20]


def test_load_bases_per_basis_lang(tmp_path):
    p = tmp_path / 'bases.tsv'
    p.write_text('basis\tfreq\tlang\ttext\nfol. mod.\t1070\tca\t\nfol. ant.\t766\t\t\n'
                 'mod.\t170\tca\tfol. mod.\n\t3\tca\t\n', encoding='utf-8')
    assert load_bases(str(p), 'es') == [('fol. mod.', 'ca', ''), ('fol. ant.', 'es', ''),
                                         ('mod.', 'ca', 'fol. mod.')]


def test_item_lang_from_philobiblon_alias():
    beta = {'es': [{'language': 'es', 'value': 'BETA manid 1234'}], 'en': [{'value': 'Otro nombre'}]}
    biteca = {'ca': [{'value': 'BITECA manid 45'}]}
    both = {'es': [{'value': 'BETA manid 1'}, {'value': 'BITECA manid 2'}]}
    assert item_lang(beta, 'ca') == 'es'
    assert item_lang(biteca, 'es') == 'ca'
    assert item_lang({'pt': [{'value': 'BITAGAP manid 9'}]}, 'ca') == 'pt'
    assert item_lang(both, 'ca') == 'ca'      # ambiguous → fallback
    assert item_lang({}, 'ca') == 'ca'
