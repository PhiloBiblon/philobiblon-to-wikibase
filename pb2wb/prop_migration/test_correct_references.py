"""Unit tests for correct_references.py (no network)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from wikibaseintegrator.models import Claim

from prop_migration.correct_references import (_p129_values, build_plan, correct_claim,
                                               sheet_target)


def _item_snak(prop, qid):
    return {'snaktype': 'value', 'property': prop, 'datatype': 'wikibase-item',
            'datavalue': {'type': 'wikibase-entityid',
                          'value': {'entity-type': 'item', 'numeric-id': int(qid[1:]), 'id': qid}}}


def _string_snak(prop, value):
    return {'snaktype': 'value', 'property': prop, 'datatype': 'string',
            'datavalue': {'type': 'string', 'value': value}}


def _claim(refs):
    return Claim().from_json({
        'mainsnak': _string_snak('P5', 'x'), 'type': 'statement', 'rank': 'normal',
        'id': 'Q1$ABC', 'references': [
            {'hash': f'h{i}', 'snaks': {s['property']: [s] for s in snaks},
             'snaks-order': [s['property'] for s in snaks]}
            for i, snaks in enumerate(refs)],
    })


def _refs(claim):
    return [{s.property_number: (s.datavalue['value']['id'] if s.datatype == 'wikibase-item'
                                 else s.datavalue['value']) for s in r.snaks}
            for r in claim.references]


def test_replace_keeps_other_snaks_and_other_refs():
    c = _claim([[_item_snak('P129', 'Q10'), _string_snak('P73', 'note')],
                [_item_snak('P129', 'Q99')]])
    assert correct_claim(c, 'Q10', 'Q20', '', '') == 'corrected'
    assert _refs(c) == [{'P129': 'Q20', 'P73': 'note'}, {'P129': 'Q99'}]


def test_replace_adds_locator():
    c = _claim([[_item_snak('P129', 'Q10')]])
    assert correct_claim(c, 'Q10', 'Q20', 'I:286', 'volume') == 'corrected'
    assert _refs(c) == [{'P129': 'Q20', 'P105': 'I', 'P54': '286'}]


def test_locator_replaces_old_locator_of_same_prop():
    c = _claim([[_item_snak('P129', 'Q10'), _string_snak('P54', '12')]])
    assert correct_claim(c, 'Q10', 'Q10', '13', 'page') == 'corrected'
    assert _refs(c) == [{'P129': 'Q10', 'P54': '13'}]


def test_already_and_missing():
    c = _claim([[_item_snak('P129', 'Q20')]])
    assert correct_claim(c, 'Q10', 'Q20', '', '') == 'already'
    assert correct_claim(c, 'Q10', 'Q30', '', '') == 'missing'
    assert _p129_values(c.references.references[0]) == ['Q20']


def _row(qid, vetted='Y', loc='', loc_type='', label='L'):
    return {'qid': qid, 'vetted': vetted, 'loc': loc, 'loc_type': loc_type, 'label': label}


def test_sheet_target_statuses():
    assert sheet_target([_row('Q5')])[0] == 'ok'
    assert sheet_target([_row('Q5', vetted='YY')])[0] == 'ok'
    assert sheet_target([_row('Q5', vetted='')])[0] == 'unvetted'
    assert sheet_target([_row('Item:Q5')])[0] == 'bad_qid'
    assert sheet_target([_row('Q5'), _row('Q6')])[0] == 'conflict'
    assert sheet_target([_row('Q5'), _row('Q5'), _row('Q7', vetted='')])[0] == 'ok'


def test_build_plan_kinds_and_skips():
    progress = [
        {'guid': 'g1', 'item': 'Q1', 'prop': 'P5', 'basis': 'A', 'qid': 'Q10', 'loc': ''},
        {'guid': 'g2', 'item': 'Q2', 'prop': 'P5', 'basis': 'B', 'qid': 'Q10', 'loc': ''},
        {'guid': 'g3', 'item': 'Q3', 'prop': 'P5', 'basis': 'C', 'qid': 'Q10', 'loc': ''},
        {'guid': 'g4', 'item': 'Q4', 'prop': 'P5', 'basis': 'D', 'qid': 'Q10', 'loc': ''},
        {'guid': 'g5', 'item': 'Q5', 'prop': 'P5', 'basis': 'E', 'qid': 'Q10', 'loc': ''},
        {'guid': 'g6', 'item': 'Q6', 'prop': 'P5', 'basis': '<i>F</i>', 'qid': 'Q10', 'loc': ''},
    ]
    sheet = {
        'A': [_row('Q20')],                          # existing item
        'B': [_row('Q2067721')],                     # new item
        'C': [_row('Q10', loc='29', loc_type='page')],   # locator only
        'D': [_row('Q10')],                          # unchanged
        'E': [_row('', vetted='')],                  # cleared by Charles
        'F': [_row('Q30', loc='sello', loc_type='annotation')],
    }
    plan, skipped = build_plan(progress, sheet, {'Q10': 'Old'})
    assert [(r['guid'], r['kind']) for r in plan] == [
        ('g1', 'existing_item'), ('g3', 'locator'), ('g2', 'new_item')]
    assert plan[0]['old_label'] == 'Old'
    assert skipped == {'unvetted': 1, 'locator type has no property': 1}
