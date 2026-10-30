"""Unit tests for correct_references.py (no network)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from wikibaseintegrator.models import Claim

from prop_migration.correct_references import (_p129_values, build_move_plan, build_plan,
                                               correct_claim, done_key, load_corrected, sheet_target,
                                               should_verify, verify_claim)


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


def test_verify_claim():
    c = _claim([[_item_snak('P129', 'Q10')]])
    assert not verify_claim(c, 'Q10', 'Q20', '', '')
    correct_claim(c, 'Q10', 'Q20', 'vii', 'page')
    assert verify_claim(c, 'Q10', 'Q20', 'vii', 'page')
    assert not verify_claim(c, 'Q10', 'Q20', 'viii', 'page')


def test_should_verify():
    assert [n for n in range(1, 31) if should_verify(n, 10)] == [1, 2, 3, 10, 20, 30]
    assert [n for n in range(1, 31) if should_verify(n, 0)] == [1, 2, 3]


# ---- move P129 → P702 (physical evidence) ----

def test_move_to_p702_keeps_locator_and_other_snaks():
    c = _claim([[_item_snak('P129', 'Q393553'), _string_snak('P100', '113'),
                 _string_snak('P73', 'note')]])
    assert correct_claim(c, 'Q393553', 'Q393553', '113', 'folio', 'P129', 'P702') == 'corrected'
    assert _refs(c) == [{'P702': 'Q393553', 'P100': '113', 'P73': 'note'}]
    assert verify_claim(c, 'Q393553', 'Q393553', '113', 'folio', 'P129', 'P702')
    # a second pass finds it already moved
    assert correct_claim(c, 'Q393553', 'Q393553', '113', 'folio', 'P129', 'P702') == 'already'


def test_move_verify_fails_while_p129_remains():
    c = _claim([[_item_snak('P129', 'Q393553')], [_item_snak('P702', 'Q393553')]])
    assert not verify_claim(c, 'Q393553', 'Q393553', '', '', 'P129', 'P702')


def test_build_move_plan_uses_corrections_and_skips_moved():
    progress = [
        {'guid': 'g1', 'item': 'Q1', 'prop': 'P5', 'basis': 'colofón', 'qid': 'Q393553', 'loc': ''},
        {'guid': 'g2', 'item': 'Q2', 'prop': 'P5', 'basis': 'Faulhaber', 'qid': 'Q10', 'loc': ''},
        {'guid': 'g3', 'item': 'Q3', 'prop': 'P5', 'basis': 'portada', 'qid': 'Q99', 'loc': ''},
        {'guid': 'g4', 'item': 'Q4', 'prop': 'P5', 'basis': '<i>sello</i>', 'qid': 'Q512065',
         'loc': '6r', 'loc_type': 'folio'},
        {'guid': 'g5', 'item': 'Q5', 'prop': 'P5', 'basis': 'guarda', 'qid': 'Q358912',
         'loc': '', 'ref_prop': 'P702'},                         # converted as P702 already
    ]
    corrections = [
        {'guid': 'g3', 'new_qid': 'Q229508', 'loc': '', 'loc_type': '', 'status': 'corrected'},
        {'guid': 'g1', 'new_qid': 'Q393553', 'loc': '', 'loc_type': '', 'status': 'missing'},
    ]
    plan = build_move_plan(progress, corrections, {'Q393553', 'Q229508', 'Q512065', 'Q358912'},
                           'P702', {'Q393553': 'Colophon'})
    assert [(r['guid'], r['old_qid'], r['old_prop'], r['new_prop'], r['loc']) for r in plan] == [
        ('g3', 'Q229508', 'P129', 'P702', ''),
        ('g1', 'Q393553', 'P129', 'P702', ''),
        ('g4', 'Q512065', 'P129', 'P702', '6r')]
    assert plan[1]['old_label'] == 'Colophon'
    assert plan[2]['basis'] == 'sello'


def test_load_corrected_keys_on_new_prop(tmp_path):
    import json
    p = tmp_path / 'c.jsonl'
    p.write_text('\n'.join(json.dumps(r) for r in [
        {'guid': 'g1', 'status': 'corrected'},                       # old record: P129
        {'guid': 'g2', 'status': 'corrected', 'new_prop': 'P702'},
        {'guid': 'g3', 'status': 'missing', 'new_prop': 'P702'},
    ]))
    assert load_corrected(str(p)) == {('g1', 'P129'), ('g2', 'P702')}


def test_add_reference_alongside_existing():
    c = _claim([[_item_snak('P129', 'Q10')]])
    assert correct_claim(c, '', 'Q20', '12', 'page') == 'added'
    assert _refs(c) == [{'P129': 'Q10'}, {'P129': 'Q20', 'P54': '12'}]
    assert correct_claim(c, '', 'Q20', '12', 'page') == 'present'
    assert len(_refs(c)) == 2
    assert verify_claim(c, '', 'Q20', '12', 'page')


def test_done_key_for_added_references(tmp_path):
    import json
    add1 = {'guid': 'g1', 'old_qid': '', 'new_qid': 'Q20', 'new_prop': 'P129'}
    add2 = dict(add1, new_qid='Q30')
    fix = {'guid': 'g1', 'old_qid': 'Q5', 'new_qid': 'Q6', 'new_prop': 'P129'}
    assert len({done_key(add1), done_key(add2), done_key(fix)}) == 3
    p = tmp_path / 'c.jsonl'
    p.write_text('\n'.join(json.dumps(dict(r, status=s)) for r, s in
                           [(add1, 'added'), (fix, 'corrected')]))
    done = load_corrected(str(p))
    assert done_key(add1) in done and done_key(fix) in done and done_key(add2) not in done
