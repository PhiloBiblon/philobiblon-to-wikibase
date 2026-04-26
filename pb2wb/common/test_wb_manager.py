"""
Tests for statement-level mutation methods in WBManager.

Uses MagicMock throughout — no live FactGrid calls.
Run from pb2wb/:  pytest common/test_wb_manager.py -v
"""

import pytest
from unittest.mock import MagicMock, patch, call

from common.wb_manager import (
    _find_claim_by_guid,
    WBManager,
)


# ---------------------------------------------------------------------------
# Helpers to build mock claim / snak objects
# ---------------------------------------------------------------------------

def _make_snak(prop, value):
    snak = MagicMock()
    snak.property_number = prop
    snak.datavalue = {'value': value, 'type': 'string'}
    return snak


def _make_claim(guid, prop='P999', qualifier_snaks=None):
    claim = MagicMock()
    claim.id = guid
    claim.mainsnak = MagicMock()
    claim.mainsnak.property_number = prop

    qs = qualifier_snaks or {}
    claim.qualifiers.get.side_effect = lambda p: qs.get(p, [])
    return claim


def _make_item(item_id, claims):
    item = MagicMock()
    item.id = item_id
    item.claims.__iter__ = MagicMock(return_value=iter(claims))
    return item


# ---------------------------------------------------------------------------
# _find_claim_by_guid
# ---------------------------------------------------------------------------

class TestFindClaimByGuid:

    def test_found(self):
        c1 = _make_claim('Q1$aaa')
        c2 = _make_claim('Q1$bbb')
        item = _make_item('Q1', [c1, c2])
        assert _find_claim_by_guid(item, 'Q1$bbb') is c2

    def test_not_found(self):
        item = _make_item('Q1', [_make_claim('Q1$aaa')])
        with pytest.raises(KeyError, match='Q1\\$zzz'):
            _find_claim_by_guid(item, 'Q1$zzz')


# ---------------------------------------------------------------------------
# WBManager fixture — patches __init__ so no network call is made
# ---------------------------------------------------------------------------

@pytest.fixture
def mgr():
    with patch.object(WBManager, '__init__', return_value=None):
        m = WBManager()
    m.wbi = MagicMock()
    return m


# ---------------------------------------------------------------------------
# get_statements_with_qualifier
# ---------------------------------------------------------------------------

class TestGetStatementsWithQualifier:

    def test_single_match(self, mgr):
        snak = _make_snak('P721', 'Faulhaber')
        claim = _make_claim('Q10$aaa', qualifier_snaks={'P721': [snak]})
        item = _make_item('Q10', [claim])
        mgr.wbi.item.get.return_value = item

        result = mgr.get_statements_with_qualifier('Q10', 'P721', 'Faulhaber')
        assert result == [('Q10$aaa', claim)]

    def test_no_match(self, mgr):
        snak = _make_snak('P721', 'Other')
        claim = _make_claim('Q10$aaa', qualifier_snaks={'P721': [snak]})
        item = _make_item('Q10', [claim])
        mgr.wbi.item.get.return_value = item

        assert mgr.get_statements_with_qualifier('Q10', 'P721', 'Faulhaber') == []

    def test_multiple_statements_one_match(self, mgr):
        s1 = _make_snak('P721', 'Faulhaber')
        s2 = _make_snak('P721', 'Other')
        c1 = _make_claim('Q10$aaa', qualifier_snaks={'P721': [s1]})
        c2 = _make_claim('Q10$bbb', qualifier_snaks={'P721': [s2]})
        item = _make_item('Q10', [c1, c2])
        mgr.wbi.item.get.return_value = item

        result = mgr.get_statements_with_qualifier('Q10', 'P721', 'Faulhaber')
        assert len(result) == 1
        assert result[0][0] == 'Q10$aaa'

    def test_no_qualifier_on_claim(self, mgr):
        claim = _make_claim('Q10$aaa')   # no P721 qualifier
        item = _make_item('Q10', [claim])
        mgr.wbi.item.get.return_value = item

        assert mgr.get_statements_with_qualifier('Q10', 'P721', 'Faulhaber') == []


# ---------------------------------------------------------------------------
# add_reference_to_statement
# ---------------------------------------------------------------------------

class TestAddReferenceToStatement:

    def test_adds_reference_and_writes(self, mgr):
        claim = _make_claim('Q10$aaa')
        item = _make_item('Q10', [claim])
        mgr.wbi.item.get.return_value = item

        with patch('common.wb_manager.time.sleep') as mock_sleep, \
             patch('common.wb_manager.WBItem') as MockWBItem:
            ref_claim = MagicMock()
            MockWBItem.return_value = ref_claim

            mgr.add_reference_to_statement('Q10', 'Q10$aaa', 'P129', 'Q999')

        MockWBItem.assert_called_once_with(value='Q999', prop_nr='P129')
        claim.references.add.assert_called_once_with(ref_claim)
        mock_sleep.assert_called_once()
        item.write.assert_called_once()

    def test_guid_not_found_raises(self, mgr):
        item = _make_item('Q10', [])
        mgr.wbi.item.get.return_value = item

        with pytest.raises(KeyError, match='Q10\\$zzz'):
            mgr.add_reference_to_statement('Q10', 'Q10$zzz', 'P129', 'Q999')
        item.write.assert_not_called()


# ---------------------------------------------------------------------------
# remove_qualifier_from_statement
# ---------------------------------------------------------------------------

class TestRemoveQualifierFromStatement:

    def test_removes_qualifier_and_writes(self, mgr):
        snak = _make_snak('P721', 'Faulhaber')
        claim = _make_claim('Q10$aaa', qualifier_snaks={'P721': [snak]})
        item = _make_item('Q10', [claim])
        mgr.wbi.item.get.return_value = item

        with patch('common.wb_manager.time.sleep') as mock_sleep:
            mgr.remove_qualifier_from_statement('Q10', 'Q10$aaa', 'P721', 'Faulhaber')

        claim.qualifiers.remove.assert_called_once_with(snak)
        mock_sleep.assert_called_once()
        item.write.assert_called_once()

    def test_value_not_found_raises(self, mgr):
        snak = _make_snak('P721', 'Other')
        claim = _make_claim('Q10$aaa', qualifier_snaks={'P721': [snak]})
        item = _make_item('Q10', [claim])
        mgr.wbi.item.get.return_value = item

        with pytest.raises(KeyError, match='Faulhaber'):
            mgr.remove_qualifier_from_statement('Q10', 'Q10$aaa', 'P721', 'Faulhaber')
        item.write.assert_not_called()

    def test_guid_not_found_raises(self, mgr):
        item = _make_item('Q10', [])
        mgr.wbi.item.get.return_value = item

        with pytest.raises(KeyError, match='Q10\\$zzz'):
            mgr.remove_qualifier_from_statement('Q10', 'Q10$zzz', 'P721', 'Faulhaber')
        item.write.assert_not_called()

    def test_removes_only_first_matching_snak(self, mgr):
        s1 = _make_snak('P721', 'Faulhaber')
        s2 = _make_snak('P721', 'Faulhaber')
        claim = _make_claim('Q10$aaa', qualifier_snaks={'P721': [s1, s2]})
        item = _make_item('Q10', [claim])
        mgr.wbi.item.get.return_value = item

        with patch('common.wb_manager.time.sleep'):
            mgr.remove_qualifier_from_statement('Q10', 'Q10$aaa', 'P721', 'Faulhaber')

        claim.qualifiers.remove.assert_called_once_with(s1)
