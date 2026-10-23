"""
factgrid_access.py — rules for talking to database.factgrid.de through the ThULB
bot filter (mod_repudiator).

* USER_AGENT was whitelisted by René Adler (ThULB), 2026-10-23. Every request to
  FactGrid must send exactly this string.
* Every response carries an X-Reputation header, e.g. "OK (-21.03)". René: if the
  value gets close to -200, stop for at least 2 minutes.
* ThULB is wary of bots making rapid reads, so every request (read or write, API or
  SPARQL) is spaced at least MIN_INTERVAL seconds after the previous one — across
  processes too, via a shared timestamp file.

Importing this module patches requests.Session.request so that every FactGrid
call (ours and WikibaseIntegrator's) obeys the rules: throttle, pause when the
reputation is low, and pause-and-retry when bounced to the challenge page.
"""

import json
import logging
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests

USER_AGENT = 'pb2wb/1.0 (PhiloBiblon P721 migration)'

FACTGRID_HOST = 'factgrid.de'
REPUTATION_PAUSE_AT = -150   # "close to -200"
PAUSE_SECONDS = 150          # "at least 2 minutes"
MAX_CHALLENGE_RETRIES = 5
MIN_INTERVAL = float(os.environ.get('FACTGRID_MIN_INTERVAL', '1.0'))   # seconds
LAST_REQUEST_FILE = 'prop_migration/run_logs/.factgrid_last_request'

# Every FactGrid response's reputation is appended here, tagged with a local network
# fingerprint (the default gateway's MAC address — no external lookup), so scores can
# be compared across home / library / coffee shop. Name fingerprints in NETWORKS_TSV.
REPUTATION_LOG = os.environ.get('FACTGRID_REPUTATION_LOG',
                                'prop_migration/run_logs/reputation.jsonl')
NETWORKS_TSV = 'prop_migration/run_logs/networks.tsv'   # fingerprint<TAB>name

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


_network = None


def network_fingerprint():
    """MAC address of the default gateway, e.g. 'a4:2b:b0:12:34:56' (cached)."""
    global _network
    if _network is None:
        try:
            route = subprocess.run(['route', '-n', 'get', 'default'], capture_output=True,
                                   text=True, timeout=5).stdout
            gw = re.search(r'gateway:\s*(\S+)', route).group(1)
            arp = subprocess.run(['arp', '-n', gw], capture_output=True,
                                 text=True, timeout=5).stdout
            _network = re.search(r' at ([0-9a-f:]+)', arp).group(1)
        except Exception:
            _network = 'unknown'
    return _network


def network_names():
    names = {}
    if os.path.exists(NETWORKS_TSV):
        with open(NETWORKS_TSV, encoding='utf-8') as f:
            for line in f:
                parts = line.rstrip('\n').split('\t')
                if len(parts) >= 2 and not line.startswith('#'):
                    names[parts[0]] = parts[1]
    return names


def _log_reputation(method, url, response, rep, event):
    try:
        os.makedirs(os.path.dirname(REPUTATION_LOG) or '.', exist_ok=True)
        with open(REPUTATION_LOG, 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                'ts': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                'network': network_fingerprint(),
                'method': method,
                'path': urlparse(str(url)).path,
                'status': response.status_code,
                'reputation': rep,
                'raw': response.headers.get('X-Reputation', ''),
                'event': event,
            }) + '\n')
    except OSError:
        pass   # logging must never break a run


def _throttle():
    """Sleep until MIN_INTERVAL has passed since the last FactGrid request (any process)."""
    if MIN_INTERVAL <= 0:
        return
    try:
        with open(LAST_REQUEST_FILE) as f:
            last = float(f.read().strip() or 0)
    except (OSError, ValueError):
        last = 0.0
    wait = last + MIN_INTERVAL - time.time()
    if wait > 0:
        time.sleep(min(wait, MIN_INTERVAL))
    try:
        os.makedirs(os.path.dirname(LAST_REQUEST_FILE) or '.', exist_ok=True)
        with open(LAST_REQUEST_FILE, 'w') as f:
            f.write(f'{time.time():.3f}')
    except OSError:
        pass


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
        _throttle()
        response = _orig_request(self, method, url, *args, **kwargs)
        rep = reputation(response)
        event = ('challenge' if challenged(response)
                 else 'low' if rep is not None and rep <= REPUTATION_PAUSE_AT else 'ok')
        _log_reputation(method, url, response, rep, event)
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
