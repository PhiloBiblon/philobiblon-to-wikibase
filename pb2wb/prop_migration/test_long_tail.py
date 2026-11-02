"""Unit tests for long_tail.py (no network)."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from wikibaseintegrator.models import Claim

from prop_migration.long_tail import (PHILOBIBLON, convert_claim, find_p721, group_by_item, guid_from_uri,
                                      load_done, ref_present, verify_claim)


def _str(prop, v):
    return {'snaktype': 'value', 'property': prop, 'datatype': 'string',
            'datavalue': {'type': 'string', 'value': v}}


def _item(prop, q):
    return {'snaktype': 'value', 'property': prop, 'datatype': 'wikibase-item',
            'datavalue': {'type': 'wikibase-entityid',
                          'value': {'entity-type': 'item', 'numeric-id': int(q[1:]), 'id': q}}}


def _ref(snaks):
    sd = {}
    for s in snaks:
        sd.setdefault(s['property'], []).append(s)
    return {'hash': str(abs(hash(str(snaks)))), 'snaks': sd, 'snaks-order': list(sd)}


def _claim(quals, refs=()):
    qd = {}
    for s in quals:
        qd.setdefault(s['property'], []).append(s)
    return Claim().from_json({
        'mainsnak': _item('P21', 'Q5'), 'type': 'statement', 'rank': 'normal',
        'id': 'Q1$ABC', 'qualifiers': qd, 'qualifiers-order': list(qd),
        'references': [_ref(r) for r in refs]})


def _refs(claim):
    return [sorted((s.property_number, s.datavalue['value'].get('id') if isinstance(s.datavalue['value'], dict)
                    else s.datavalue['value']) for s in r.snaks) for r in claim.references]


def test_guid_from_uri():
    uri = 'https://database.factgrid.de/entity/statement/Q425307-1B2C3D4E-AAAA-BBBB-CCCC-0123456789AB'
    assert guid_from_uri(uri) == 'Q425307$1B2C3D4E-AAAA-BBBB-CCCC-0123456789AB'
    assert guid_from_uri('…/statement/q12-abc-def') == 'Q12$abc-def'


def test_convert_adds_reference_and_removes_qualifier():
    c = _claim([_str('P721', 'Marín xiii'), _str('P54', '12')])
    assert convert_claim(c, 'Marín xiii') == 'converted'
    assert find_p721(c, 'Marín xiii') is None
    assert [s.property_number for s in c.qualifiers.get('P54')] == ['P54']   # other qualifiers kept
    assert _refs(c) == [[('P129', PHILOBIBLON), ('P73', 'Marín xiii')]]
    assert verify_claim(c, 'Marín xiii')


def test_existing_references_kept():
    c = _claim([_str('P721', 'Riquer 1963 I:171')], refs=[[_item('P129', 'Q1068197'), _str('P54', '3')]])
    convert_claim(c, 'Riquer 1963 I:171')
    assert _refs(c) == [[('P129', 'Q1068197'), ('P54', '3')],
                        [('P129', PHILOBIBLON), ('P73', 'Riquer 1963 I:171')]]


def test_two_p721_values_on_one_claim_give_two_references():
    c = _claim([_str('P721', 'Andrés'), _str('P721', 'muerte')])
    assert convert_claim(c, 'Andrés') == 'converted'
    assert [s.datavalue['value'] for s in c.qualifiers.get('P721')] == ['muerte']   # only that one removed
    assert convert_claim(c, 'muerte') == 'converted'
    assert not c.qualifiers.get('P721')
    assert len(c.references) == 2


def test_identical_reference_not_duplicated():
    c = _claim([_str('P721', 'Andrés')], refs=[[_item('P129', PHILOBIBLON), _str('P73', 'Andrés')]])
    assert ref_present(c, 'Andrés')
    assert convert_claim(c, 'Andrés') == 'converted'
    assert len(c.references) == 1
    assert find_p721(c, 'Andrés') is None


def test_reference_with_other_note_is_not_a_match():
    c = _claim([_str('P721', 'Andrés')], refs=[[_item('P129', PHILOBIBLON), _str('P73', 'Andrés xxvi')]])
    assert not ref_present(c, 'Andrés')
    convert_claim(c, 'Andrés')
    assert len(c.references) == 2


def test_gone_when_value_absent():
    c = _claim([_str('P721', 'Andrés')])
    assert convert_claim(c, '<i>Andrés</i>') == 'gone'           # exact match only
    assert find_p721(c, 'Andrés') is not None
    assert len(c.references) == 0


def test_html_basis_kept_word_for_word():
    c = _claim([_str('P721', '<i>DHEE</i> 1875')])
    assert convert_claim(c, '<i>DHEE</i> 1875') == 'converted'
    assert _refs(c) == [[('P129', PHILOBIBLON), ('P73', '<i>DHEE</i> 1875')]]
    assert verify_claim(c, '<i>DHEE</i> 1875')


def test_verify_fails_if_p721_still_there():
    c = _claim([_str('P721', 'Andrés')], refs=[[_item('P129', PHILOBIBLON), _str('P73', 'Andrés')]])
    assert not verify_claim(c, 'Andrés')


def test_group_by_item_skips_done(tmp_path):
    log = tmp_path / 'lt.jsonl'
    log.write_text('\n'.join(json.dumps(r) for r in [
        {'guid': 'Q1$a', 'basis': 'x', 'status': 'converted'},
        {'guid': 'Q2$b', 'basis': 'y', 'status': 'error'},
        {'guid': 'Q3$c', 'basis': 'z', 'status': 'missing'},
    ]) + '\nnot json\n', encoding='utf-8')
    done = load_done(str(log))
    assert done == {('Q1$a', 'x')}
    plan = [{'item': 'Q1', 'guid': 'Q1$a', 'basis': 'x'}, {'item': 'Q1', 'guid': 'Q1$a', 'basis': 'w'},
            {'item': 'Q2', 'guid': 'Q2$b', 'basis': 'y'}]
    g = group_by_item(plan, done)
    assert list(g) == ['Q1', 'Q2']
    assert [r['basis'] for r in g['Q1']] == ['w']
