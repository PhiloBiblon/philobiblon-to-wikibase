"""Unit tests for common/factgrid_access.py (no network)."""

import os
import sys
from unittest import mock

import pytest
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import common.factgrid_access as fa


def _resp(rep=None, url='https://database.factgrid.de/w/api.php', location=None):
    r = requests.Response()
    r.status_code = 200
    r.url = url
    if rep is not None:
        r.headers['X-Reputation'] = rep
    if location:
        r.headers['Location'] = location
    return r


@pytest.mark.parametrize('header,expected', [
    ('OK (-21.03)', -21.03),
    ('WARN (-200.21)', -200.21),
    ('OK (299.79)', 299.79),
])
def test_reputation_parses_header(header, expected):
    assert fa.reputation(_resp(header)) == expected


def test_reputation_missing():
    assert fa.reputation(_resp()) is None


def test_challenged_by_url_or_location():
    assert fa.challenged(_resp(url='https://database.factgrid.de/rep-pow-challenge?x=1'))
    assert fa.challenged(_resp(location='/rep-pow-challenge?redirect_uri=%2f'))
    assert not fa.challenged(_resp())


def _run(responses):
    """Call the guarded request with canned responses; return (result, sleeps, calls)."""
    calls = []

    def fake_orig(self, method, url, *args, **kwargs):
        calls.append(kwargs.get('headers', {}))
        return responses.pop(0)

    with mock.patch.object(fa, '_orig_request', fake_orig), \
         mock.patch.object(fa.time, 'sleep') as sleep:
        result = fa._guarded_request(requests.Session(), 'GET',
                                     'https://database.factgrid.de/w/api.php')
    return result, sleep.call_count, calls


def test_good_reputation_no_pause():
    _, sleeps, calls = _run([_resp('OK (-21.03)')])
    assert sleeps == 0
    assert calls[0]['User-Agent'] == fa.USER_AGENT


def test_low_reputation_pauses_once():
    _, sleeps, _ = _run([_resp('WARN (-190.00)')])
    assert sleeps == 1


def test_challenge_pauses_and_retries():
    ok = _resp('OK (10.0)')
    result, sleeps, calls = _run([_resp(url='https://database.factgrid.de/rep-pow-challenge'), ok])
    assert result is ok
    assert sleeps == 1
    assert len(calls) == 2


def test_persistent_challenge_raises():
    bounced = [_resp(url='https://database.factgrid.de/rep-pow-challenge')
               for _ in range(fa.MAX_CHALLENGE_RETRIES + 1)]
    with pytest.raises(RuntimeError, match='still whitelisted'):
        _run(bounced)


def test_other_hosts_untouched():
    seen = []

    def fake_orig(self, method, url, *args, **kwargs):
        seen.append(kwargs.get('headers'))
        return _resp('WARN (-500)', url=url)

    with mock.patch.object(fa, '_orig_request', fake_orig), \
         mock.patch.object(fa.time, 'sleep') as sleep:
        fa._guarded_request(requests.Session(), 'GET', 'https://example.org/')
    assert sleep.call_count == 0
    assert seen == [None]
