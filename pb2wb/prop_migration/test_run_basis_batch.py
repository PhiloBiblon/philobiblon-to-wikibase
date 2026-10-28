"""Unit tests for run_basis_batch planning and prop_migration/locators.py (no network)."""

import json
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


# ---- apply_basis_migration: re-login on expired session ----

import prop_migration.apply_basis_migration as abm


class _FakeItem:
    def __init__(self, errors):
        self.errors = list(errors)
        self.logins = []

    def write(self, login=None):
        self.logins.append(login)
        if self.errors:
            raise self.errors.pop(0)
        return 'written'


def test_write_item_relogins_once_on_expired_session(monkeypatch):
    calls = []
    monkeypatch.setattr(abm, '_relogin', lambda: calls.append(1) or 'NEW-LOGIN')
    item = _FakeItem([Exception("You're no longer logged in")])
    assert abm._write_item(item, None) == 'written'
    assert calls == [1]
    assert item.logins == [None, 'NEW-LOGIN']


def test_write_item_other_errors_propagate(monkeypatch):
    monkeypatch.setattr(abm, '_relogin', lambda: pytest.fail('should not re-login'))
    item = _FakeItem([Exception('external client site did not provide page information')])
    with pytest.raises(Exception, match='external client site'):
        abm._write_item(item, None)


def test_write_item_gives_up_after_one_relogin(monkeypatch):
    monkeypatch.setattr(abm, '_relogin', lambda: 'NEW-LOGIN')
    item = _FakeItem([Exception('anonymous token'), Exception('anonymous token')])
    with pytest.raises(Exception, match='anonymous token'):
        abm._write_item(item, None)


# ---- runner: include/exclude lists, one login per run ----

from prop_migration import run_basis_batch as rbb


def test_load_basis_list(tmp_path):
    p = tmp_path / 'list.tsv'
    p.write_text('# held\nFaulhaber 2006\nfichero\tmodeling question\n\n', encoding='utf-8')
    assert rbb.load_basis_list(str(p)) == {'Faulhaber 2006', 'fichero'}


def _setup(tmp_path):
    sheet = tmp_path / 'sheet.tsv'
    sheet.write_text('Freqency\tbasis\tkey\tmatch_type\tqid\tlabel\tvetted\tloc_type\tloc\n'
                     '9\tAlpha\tAlpha\tvetted\tQ1\tA\tY\t\t\n'
                     '8\tBeta\tBeta\tvetted\tQ2\tB\tYY\t\t\n'
                     '7\tGamma\tGamma\tvetted\tQ3\tG\tY\t\t\n', encoding='utf-8')
    live = tmp_path / 'live.tsv'
    live.write_text('value\tfreq\nAlpha\t5\nBeta\t4\nGamma\t3\n', encoding='utf-8')
    include = tmp_path / 'include.txt'
    include.write_text('Alpha\nBeta\nGamma\n', encoding='utf-8')
    exclude = tmp_path / 'exclude.tsv'
    exclude.write_text('Gamma\tworks vs people\n', encoding='utf-8')
    return sheet, live, include, exclude


def test_runner_logs_in_once_and_skips_bad_config(tmp_path, monkeypatch):
    sheet, live, include, exclude = _setup(tmp_path)
    calls = {'connect': 0, 'run': [], 'sleep': 0}

    monkeypatch.setattr(abm, 'ping_api', lambda: True)
    monkeypatch.setattr(abm, 'connect', lambda: calls.__setitem__('connect', calls['connect'] + 1) or 'WBI')

    def fake_run(basis, wbi, **kw):
        calls['run'].append((basis, wbi))
        if basis == 'Beta':
            raise abm.BasisConfigError('no property for loc_type')
        return {'converted': 1, 'skipped': 0, 'errors': 0}

    monkeypatch.setattr(abm, 'run_basis', fake_run)
    monkeypatch.setattr(rbb.time, 'sleep', lambda s: calls.__setitem__('sleep', calls['sleep'] + 1))
    monkeypatch.setattr(sys, 'argv', [
        'run_basis_batch.py', '--tsv', str(sheet), '--live-counts', str(live),
        '--include', str(include), '--exclude', str(exclude),
        '--progress-log', str(tmp_path / 'progress.jsonl'),
        '--batch-log', str(tmp_path / 'batch.jsonl')])
    rbb.main()

    assert calls['connect'] == 1                                  # one login for the run
    assert calls['run'] == [('Alpha', 'WBI'), ('Beta', 'WBI')]    # Gamma excluded
    assert calls['sleep'] == 0                                    # config error: no maintenance wait


def test_runner_dry_run_never_connects(tmp_path, monkeypatch):
    sheet, live, include, _ = _setup(tmp_path)
    monkeypatch.setattr(abm, 'connect', lambda: pytest.fail('dry run must not log in'))
    monkeypatch.setattr(abm, 'ping_api', lambda: pytest.fail('dry run must not ping'))
    monkeypatch.setattr(sys, 'argv', [
        'run_basis_batch.py', '--tsv', str(sheet), '--live-counts', str(live),
        '--include', str(include), '--dry-run',
        '--progress-log', str(tmp_path / 'progress.jsonl'),
        '--batch-log', str(tmp_path / 'batch.jsonl')])
    rbb.main()


def test_conversions_since(tmp_path):
    p = tmp_path / 'progress.jsonl'
    p.write_text('\n'.join(json.dumps(r) for r in [
        {'basis': 'A', 'ts': '2026-10-26T17:00:00+00:00'},
        {'basis': '<i>A</i>', 'ts': '2026-10-26T18:30:00+00:00'},
        {'basis': 'B', 'ts': '2026-10-26T18:40:00+00:00'},
    ]) + '\n', encoding='utf-8')
    assert rbb.conversions_since(str(p), '2026-10-26T18:01:00+00:00') == {'A': 1, 'B': 1}


# ---- reference property: P702 "Based on" for physical evidence ----

def test_runner_passes_ref_prop(tmp_path, monkeypatch):
    sheet, live, include, exclude = _setup(tmp_path)
    seen = []
    monkeypatch.setattr(abm, 'ping_api', lambda: True)
    monkeypatch.setattr(abm, 'connect', lambda: 'WBI')
    monkeypatch.setattr(abm, 'run_basis',
                        lambda basis, wbi, **kw: seen.append(kw['ref_prop']) or {'converted': 1})
    monkeypatch.setattr(sys, 'argv', [
        'run_basis_batch.py', '--tsv', str(sheet), '--live-counts', str(live),
        '--include', str(include), '--exclude', str(exclude), '--ref-prop', 'P702',
        '--progress-log', str(tmp_path / 'progress.jsonl'),
        '--batch-log', str(tmp_path / 'batch.jsonl')])
    rbb.main()
    assert seen == ['P702', 'P702']


def _p721_claim(basis):
    from wikibaseintegrator.models import Claim
    s = lambda p, v: {'snaktype': 'value', 'property': p, 'datatype': 'string',
                      'datavalue': {'type': 'string', 'value': v}}
    return Claim().from_json({
        'mainsnak': s('P5', 'x'), 'type': 'statement', 'rank': 'normal', 'id': 'Q1$G1',
        'qualifiers': {'P721': [s('P721', basis)]}, 'qualifiers-order': ['P721'],
        'references': []})


class _FakeWbiItem:
    def __init__(self, claims):
        self.claims = claims
        self.writes = 0

    def write(self, login=None):
        self.writes += 1


def test_process_item_writes_p702_reference(tmp_path, monkeypatch):
    claim = _p721_claim('colofón')
    item = _FakeWbiItem([claim])
    wbi = type('W', (), {'item': type('I', (), {'get': staticmethod(lambda qid: item)})(),
                         'session': None})()
    log_path = tmp_path / 'progress.jsonl'
    guids, skipped, errors = abm.process_item(
        wbi, 'Q1', 'colofón', 'Q393553', 'f. 113', 'folio', set(), False, 0, str(log_path),
        ref_prop='P702')
    assert (guids, skipped, errors) == (['Q1$G1'], 0, 0)
    assert item.writes == 2
    ref = claim.references.references[0]
    assert [sn.property_number for sn in ref.snaks] == ['P702', 'P100']
    assert not claim.qualifiers.get('P721')
    rec = json.loads(log_path.read_text())
    assert rec['ref_prop'] == 'P702' and rec['qid'] == 'Q393553'
    # already present as P702 → not added again
    assert abm._ref_present(claim, 'Q393553', 'P702')
    assert not abm._ref_present(claim, 'Q393553')


def test_log_progress_omits_default_ref_prop(tmp_path):
    p = tmp_path / 'progress.jsonl'
    abm.log_progress(str(p), 'g', 'Q1', 'b', 'Q2', '', '')
    assert 'ref_prop' not in json.loads(p.read_text())


def test_run_basis_rejects_other_ref_props():
    with pytest.raises(abm.BasisConfigError, match='ref_prop'):
        abm.run_basis('x', None, ref_prop='P73')


# ---- locators garbled into times by Google Sheets ----

from prop_migration.locators import repair_loc


@pytest.mark.parametrize('basis,loc,expected', [
    ('Arteaga 1:227', '4:47', '1:227'),
    ('Arteaga 1:301', '6:01', '1:301'),
    ('IGM 2:131', '4:11:00', '2:131'),
    ('Moita (2017), O Livro hebraico português…, vol. 2, p. 62', '3:02', '2:62'),
    ('Godinho (2011), vol. 1, p. 206', '4:26', '1:206'),
    ('Moreno (1987), Exiliados portugueses…, 1: 73', '2:13', '1:73'),
    ('Arteaga I:286', 'I:286', 'I:286'),        # Roman volume: never mangled
    ('Arteaga 1:91, 102', '1:91, 102', '1:91, 102'),
    ('Zarco 4:47', '4:47', '4:47'),              # time-shaped but genuine
    ('Beltrán 1997:60', '60', '60'),
    ('Foo 3:45', '9:99', '9:99'),                # no matching basis pair: left alone
    ('X', '', ''),
])
def test_repair_loc(basis, loc, expected):
    assert repair_loc(basis, loc) == expected


def test_load_candidates_repairs_time_locators(tmp_path):
    sheet = tmp_path / 'sheet.tsv'
    sheet.write_text('Freqency\tbasis\tkey\tmatch_type\tqid\tlabel\tvetted\tloc_type\tloc\n'
                     '4\tArteaga 1:227\tArteaga\tvetted\tQ1\tA\tY\tvolume\t4:47\n', encoding='utf-8')
    assert rbb.load_candidates(str(sheet), None, None) == [(4, 'Arteaga 1:227', 'Q1', '1:227', 'volume')]
    assert abm.load_candidate('Arteaga 1:227', str(sheet))['loc'] == '1:227'
