"""
factgrid_access.py — rules for talking to database.factgrid.de through the ThULB
bot filter (mod_repudiator).

* USER_AGENT was whitelisted by René Adler (ThULB), 2026-10-23. Every request to
  FactGrid must send exactly this string.
* Every response carries an X-Reputation header, e.g. "OK (-21.03)". René: if the
  value gets close to -200, stop for at least 2 minutes.

Importing this module patches requests.Session.request so that every FactGrid
call (ours and WikibaseIntegrator's) obeys the rule: pause when the reputation is
low, and pause-and-retry when a request is bounced to the challenge page.
"""

import logging
import re
import time

import requests

USER_AGENT = 'pb2wb/1.0 (PhiloBiblon P721 migration)'

FACTGRID_HOST = 'factgrid.de'
REPUTATION_PAUSE_AT = -150   # "close to -200"
PAUSE_SECONDS = 150          # "at least 2 minutes"
MAX_CHALLENGE_RETRIES = 5

_REP_RE = re.compile(r'\((-?\d+(?:\.\d+)?)\)')
log = logging.getLogger(__name__)


def reputation(response):
    """Return the X-Reputation score as a float, or None if absent."""
    m = _REP_RE.search(response.headers.get('X-Reputation', ''))
    return float(m.group(1)) if m else None


def challenged(response):
    """True if the request was bounced to the proof-of-work challenge."""
    if 'rep-pow-challenge' in response.url:
        return True
    return 'rep-pow-challenge' in response.headers.get('Location', '')


def _pause(reason):
    log.warning('FactGrid %s — pausing %ds', reason, PAUSE_SECONDS)
    print(f'FactGrid {reason} — pausing {PAUSE_SECONDS}s', flush=True)
    time.sleep(PAUSE_SECONDS)


_orig_request = requests.Session.request


def _guarded_request(self, method, url, *args, **kwargs):
    if FACTGRID_HOST not in str(url):
        return _orig_request(self, method, url, *args, **kwargs)
    headers = kwargs.get('headers') or {}
    if headers.get('User-Agent') != USER_AGENT:
        kwargs['headers'] = {**headers, 'User-Agent': USER_AGENT}
    for attempt in range(MAX_CHALLENGE_RETRIES + 1):
        response = _orig_request(self, method, url, *args, **kwargs)
        rep = reputation(response)
        if challenged(response):
            if attempt == MAX_CHALLENGE_RETRIES:
                raise RuntimeError(f'FactGrid bot challenge persists after {attempt} retries '
                                   f'(X-Reputation={rep}); is the User-Agent still whitelisted?')
            _pause(f'bot challenge (X-Reputation={rep})')
            continue
        if rep is not None and rep <= REPUTATION_PAUSE_AT:
            _pause(f'reputation low ({rep})')
        return response


if not getattr(requests.Session.request, '_factgrid_guarded', False):
    _guarded_request._factgrid_guarded = True
    requests.Session.request = _guarded_request
