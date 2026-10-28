"""Unit tests for job_queue.py (no network)."""

import json
import os
import sys
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import prop_migration.job_queue as jq


@pytest.mark.parametrize('utc,et', [
    ('2026-10-27T23:30:00', '19:30'),   # EDT (UTC-4)
    ('2026-11-02T00:30:00', '19:30'),   # EST (UTC-5) after Nov 1
    ('2026-03-09T00:30:00', '20:30'),   # EDT starts Mar 8, 2026
])
def test_eastern_now(utc, et):
    now = datetime.fromisoformat(utc).replace(tzinfo=timezone.utc)
    assert jq.eastern_now(now).strftime('%H:%M') == et


def test_in_maintenance():
    d = datetime(2026, 10, 27)
    assert not jq.in_maintenance(d.replace(hour=18, minute=49))
    assert jq.in_maintenance(d.replace(hour=18, minute=50))
    assert jq.in_maintenance(d.replace(hour=19, minute=49))
    assert not jq.in_maintenance(d.replace(hour=19, minute=50))


def test_log_problems():
    ok = 'Spot-check: 3 OK, 0 FAILED, 0 errors\nConverted : 9'
    assert jq.log_problems(ok) == []
    bad = 'x\nSpot-check: 2 OK, 1 FAILED, 0 errors\nQ1  Q1$X: READ-BACK FAILED\n3 items failed in a row — stopping'
    assert len(jq.log_problems(bad)) == 3


def test_reputation_problems():
    lines = [json.dumps({'ts': '2026-10-27T10:00:00+00:00', 'event': 'low', 'reputation': -160}),
             json.dumps({'ts': '2026-10-27T12:00:00+00:00', 'event': 'ok', 'reputation': 400}),
             json.dumps({'ts': '2026-10-27T12:05:00+00:00', 'event': 'challenge', 'reputation': -210})]
    assert jq.reputation_problems(lines, '2026-10-27T11:00:00+00:00') == [
        '2026-10-27T12:05:00+00:00 challenge -210']


# ---- end-to-end worker runs with dummy jobs ----

@pytest.fixture
def qdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs('prop_migration/run_logs')
    monkeypatch.setattr(jq, 'eastern_now', lambda now_utc=None: datetime(2026, 10, 27, 12, 0))
    return tmp_path


def _add(name, code):
    jq.cmd_add(SimpleNamespace(name=name, cmd=['--', '{python}', '-c', code]))


def _states():
    return {s: sorted(json.load(open(p))['name'] for p in jq._jobs(s)) for s in jq.STATES}


def test_worker_runs_all_good_jobs(qdir):
    _add('one', 'print("Spot-check: 3 OK, 0 FAILED, 0 errors")')
    _add('two', 'print("fine")')
    jq.cmd_work(None)
    assert _states() == {'queue': [], 'running': [], 'done': ['one', 'two'], 'failed': []}
    assert 'Spot-check' in open('prop_migration/run_logs/job_one.log').read()


def test_worker_stops_on_failed_job(qdir):
    _add('a_bad', 'import sys; sys.exit(3)')
    _add('b_next', 'print("never runs")')
    jq.cmd_work(None)
    assert _states() == {'queue': ['b_next'], 'running': [], 'done': [], 'failed': ['a_bad']}


def test_worker_stops_on_readback_failure(qdir):
    _add('a_rb', 'print("Q1  Q1$X: READ-BACK FAILED")')
    _add('b_next', 'print("never runs")')
    jq.cmd_work(None)
    assert _states()['failed'] == ['a_rb'] and _states()['queue'] == ['b_next']


def test_stop_file(qdir):
    _add('a', 'print(1)')
    jq.cmd_stop(None)
    jq.cmd_work(None)
    assert _states()['queue'] == ['a'] and not os.path.exists(jq.STOP_FILE)
