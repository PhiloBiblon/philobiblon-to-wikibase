"""
generate_basis_mapping.py — iterative search pass for P721 basis/reference migration.

Reads the pulled Google Sheet TSV (P721-P129.tsv), re-processes all rows where
vetted is blank, and writes a candidates TSV for review/merge.

Rows already marked vetted (Y or auto) are passed through unchanged.
Rows where vetted is blank are re-preprocessed from the basis string and
re-searched via the wbsearchentities API.  This means Charles's or Max's
corrections to the basis column are automatically picked up on re-run.

Pre-processing pipeline (applied in order after HTML stripping):
  excluded      — non-reference strings (fol. mod., ?, princeps, etc.)
  compound      — contains ' / '; skip search, flag for manual handling
  dhee          — "DHEE <loc>" → key=DHEE, loc=<loc>
  auth_year_loc — "Author 1997:60" → key="Author 1997", loc="60"
  roman_vol     — "Author I:286" → key="Author", loc="I:286"
  auth_year     — "Author 2006" → key="Author 2006", loc=""
  raw           — no pattern matched; key = whole string

loc_type is inferred from the loc component:
  folio    — e.g. "93v", "f. 3r"
  footnote — e.g. "27n"
  ''       — plain page number or unrecognised

match_type values in output:
  vetted       — row was already vetted (Y/auto) in the sheet; passed through
  excluded     — non-reference string, not searched
  compound     — contains ' / ', needs manual handling
  api_label    — exact label match via wbsearchentities
  api_alias    — exact alias match via wbsearchentities
  api_fuzzy    — API returned a hit but text differs from key
  none         — no API match; key was produced by a known parse pattern
  llm_pending  — no parse pattern matched and no clean API hit; needs LLM

Usage (from pb2wb/):
    python prop_migration/generate_basis_mapping.py
    python prop_migration/generate_basis_mapping.py --sheet prop_migration/P721-P129.tsv
    python prop_migration/generate_basis_mapping.py --limit 20   # top N unvetted rows
    python prop_migration/generate_basis_mapping.py --dry-run
    python prop_migration/generate_basis_mapping.py --out prop_migration/basis_candidates.tsv
"""

import os
import sys
import re
import csv
import argparse
import unicodedata

dir_path = os.path.dirname(os.path.realpath(__file__))
parent_dir_path = os.path.dirname(dir_path)
sys.path.append(parent_dir_path)

import requests
from tqdm import tqdm
from common.settings import BASE_IMPORT_OBJECTS

FG = BASE_IMPORT_OBJECTS['FACTGRID']

SHEET_TSV = 'prop_migration/P721-P129.tsv'
OUT_TSV   = 'prop_migration/basis_candidates.tsv'

OUT_COLUMNS = [
    'freq', 'basis', 'key',
    'match_type', 'qid', 'label', 'vetted',
    'loc', 'loc_type',
    'col_folio', 'col_page', 'col_volume', 'col_date', 'col_footnote', 'col_literal',
]

# Strings that are not bibliographic references and should be excluded.
# Stored lower-cased for comparison after strip_html + .lower().
EXCLUDED_VALUES = {
    'fol. mod.', 'fol. ant.', 'ant.', 'mod.', '[?]', '?',
    'princeps', 'fol. antiga', 'fol. manuscrita',
    'fol. moderna', 'fol. antigua', 'manuscrita', 'moderna', 'antiga',
    # Catalan manuscript notation variants
    'fol. ant. en xifres romanes', 'fol. ant. en romans',
    'fol. moderna a llapis', 'fol. ant. en xifres aràbigues',
    'fol. moderna en xifres aràbigues',
}

# Regex patterns for exclusion — applied case-insensitively after strip_html.
# Covers families of variants too broad for exact matching.
EXCLUDED_PATTERNS = [
    re.compile(r'^wikidata',    re.IGNORECASE),  # Wikidata, WIkidata, Wikidata (2012-), …
    re.compile(r'^wikipedia',   re.IGNORECASE),  # Wikipedia, WIkipedia, Wikipedia en español, …
    re.compile(r'\bfichero\b',  re.IGNORECASE),  # fichero, fichero de Palacio, BNE fichero, …
    re.compile(r'^oskicat',     re.IGNORECASE),  # OskiCat, OskICat, Oskicat, …
    re.compile(r'^https?://',   re.IGNORECASE),  # bare URLs
]

# Compound references: two sources separated by " / "
COMPOUND_RE = re.compile(r'\s/\s')

# Shelfmarks: slash not surrounded by spaces (e.g. BNE MSS/7811, Frankfurt a/M: …)
SHELFMARK_RE = re.compile(r'(?<! )/|/(?! )')

# DHEE followed by a locator (looks like a year but is a page number)
DHEE_RE = re.compile(r'^DHEE\s+(\S+)\s*$', re.IGNORECASE)

# Author + 4-digit year + colon + locator  e.g. "Beltrán 1997:60"
AUTH_YEAR_LOC_RE = re.compile(r'^(.+?\s+\d{4}):(.+)$')

# Roman-numeral volume + arabic page  e.g. "Arteaga I:286"
# Requires at least one uppercase Roman-numeral letter before the colon.
ROMAN_VOL_RE = re.compile(r'^(.+?)\s+([IVXLCDM]+:\d+\S*)\s*$')

# Author + year (plain, range, or parenthesised) with no locator after a colon.
# Matches: "Hernández 2006", "Dutton 1990-91", "Faria (2021)",
#          "Moreno (1979-80)", "Resende et al. (1990-2003)", "CORDE (1992-)"
AUTH_YEAR_RE = re.compile(
    r'^.+\s+'
    r'(?:\d{4}'              # plain year: 2006
    r'|\d{4}-\d{2,4}'        # year range: 1990-91, 1990-1997
    r'|\(\d{4}\)'            # (2021)
    r'|\(\d{4}-\d{2,4}\)'   # (1979-80), (1990-2003)
    r'|\(\d{4}-\)'           # (2012-)  — ongoing work
    r')$'
)

# Folio locator:  "93v", "3r", "f. 93v", "f.3r"
FOLIO_LOC_RE = re.compile(r'^(f\.?\s*)?\d+[rv]$', re.IGNORECASE)

# Footnote locator:  "27n"
FOOTNOTE_LOC_RE = re.compile(r'^\d+n$')

# Volume:page locator in loc, e.g. "I:286", "XIV:45", "4:60"
_VOL_PAGE_RE = re.compile(r'^([IVXLCDMivxlcdm]+|\d+):(.+)$')

# Page-like content: digits, ranges, comma-separated — but not free text
_PAGE_LIKE_RE = re.compile(r'^\d[\d\s,\-–]*$')

# Four-digit year bounds for col_date
_YEAR_RE = re.compile(r'^(\d{4})$')
_YEAR_MIN, _YEAR_MAX = 1500, 2100

# PhiloBiblon bibliographic-ID alias pattern: "BETA bibid 1234"
_BIBID_RE = re.compile(r'^(BETA|BITAGAP|BITECA)\s+bibid\s+\d+', re.IGNORECASE)

# Description keywords that signal a reference/bibliographic work
_REF_DESC_RE = re.compile(r'reference|bibliograph|critical edition|scholarly|obra|trabajo', re.IGNORECASE)

# Description keywords that disqualify a candidate — these are never reference sources
_REJECT_DESC_RE = re.compile(r'\bfamily name\b|\bsurname\b|\bgiven name\b|\bforename\b|\bcognomen\b', re.IGNORECASE)

_FG_WIKI_BASE = 'https://database.factgrid.de/wiki/Item:'


# ---------------------------------------------------------------------------
# Pre-processing helpers
# ---------------------------------------------------------------------------

def strip_html(s):
    """Remove HTML tags from s."""
    return re.sub(r'<[^>]+>', '', s).strip()


def is_excluded(s):
    """Return True if s is a non-reference string (exact set or regex pattern)."""
    stripped = s.strip()
    if stripped.lower() in EXCLUDED_VALUES:
        return True
    return any(p.search(stripped) for p in EXCLUDED_PATTERNS)


def detect_loc_type(loc):
    """Infer the type of a locator string: 'folio', 'footnote', 'page', or ''."""
    if not loc:
        return ''
    if FOOTNOTE_LOC_RE.match(loc):
        return 'footnote'
    if FOLIO_LOC_RE.match(loc):
        return 'folio'
    return 'page'


def parse_loc_columns(loc, loc_type, parse_pattern=''):
    """
    Decompose loc + loc_type into typed col_ fields for the FactGrid reference block.
    Returns a dict with keys: col_folio, col_page, col_volume, col_date,
    col_footnote, col_literal.

    parse_pattern='dhee' forces the locator into col_page regardless of whether
    it looks like a year — DHEE locators are page numbers, not publication dates.
    """
    result = {
        'col_folio': '', 'col_page': '', 'col_volume': '',
        'col_date': '', 'col_footnote': '', 'col_literal': '',
    }
    if not loc:
        return result
    if loc_type == 'folio':
        result['col_folio'] = loc
    elif loc_type == 'footnote':
        result['col_footnote'] = loc
    elif loc_type == 'page':
        m = _YEAR_RE.match(loc)
        if m and _YEAR_MIN <= int(m.group(1)) <= _YEAR_MAX and parse_pattern != 'dhee':
            result['col_date'] = loc
        else:
            m = _VOL_PAGE_RE.match(loc)
            if m:
                result['col_volume'] = m.group(1)
                result['col_page'] = m.group(2)
            elif _PAGE_LIKE_RE.match(loc):
                result['col_page'] = loc
            else:
                result['col_literal'] = loc
    else:
        result['col_literal'] = loc
    return result


def preprocess(raw):
    """
    Strip HTML, classify, and parse key/loc/loc_type from a raw P721 string.

    Returns a dict:
      basis         — HTML-stripped string
      key           — searchable component (sent to wbsearchentities)
      loc           — locator/page component
      loc_type      — '', 'folio', 'footnote'
      preproc_type  — '', 'excluded', 'compound'
      parse_pattern — rule that fired: 'dhee', 'auth_year_loc', 'roman_vol',
                      'auth_year', 'raw'
    """
    basis = strip_html(raw)

    if is_excluded(basis):
        return _pp(basis, basis, '', '', 'excluded', 'raw')

    if COMPOUND_RE.search(basis):
        return _pp(basis, basis, '', '', 'compound', 'raw')

    m = DHEE_RE.match(basis)
    if m:
        loc = m.group(1)
        return _pp(basis, 'DHEE', loc, detect_loc_type(loc), '', 'dhee')

    m = AUTH_YEAR_LOC_RE.match(basis)
    if m:
        key = m.group(1).strip()
        loc = m.group(2).strip()
        return _pp(basis, key, loc, detect_loc_type(loc), '', 'auth_year_loc')

    m = ROMAN_VOL_RE.match(basis)
    if m:
        key = m.group(1).strip()
        loc = m.group(2).strip()
        return _pp(basis, key, loc, detect_loc_type(loc), '', 'roman_vol')

    if AUTH_YEAR_RE.match(basis):
        return _pp(basis, basis.strip(), '', '', '', 'auth_year')

    if SHELFMARK_RE.search(basis):
        return _pp(basis, basis.strip(), '', '', '', 'shelfmark')

    return _pp(basis, basis.strip(), '', '', '', 'raw')


def _pp(basis, key, loc, loc_type, preproc_type, parse_pattern):
    return {
        'basis':         basis,
        'key':           key,
        'loc':           loc,
        'loc_type':      loc_type,
        'preproc_type':  preproc_type,
        'parse_pattern': parse_pattern,
    }


# ---------------------------------------------------------------------------
# Sheet loader
# ---------------------------------------------------------------------------

def extract_qid(cell_value):
    """Extract bare QID from plain text, HYPERLINK formula, or URL."""
    m = re.search(r'Q\d+', cell_value)
    return m.group(0) if m else ''


def load_sheet(path, refresh=False):
    """
    Read the sheet TSV and return three lists:

      vetted_rows   — vetted=Y/auto with qid; output as match_type='vetted'
      resolved_rows — already searched (match_type set, not llm_pending);
                      passed through with original match_type, no re-search
      pending_rows  — llm_pending or no match_type yet; (re-)preprocessed
                      and searched; sorted by descending freq

    refresh=True moves match_type='none' rows from resolved to pending so they
    are re-queried (use after new FactGrid items have been created).
    """
    vetted_rows   = []
    resolved_rows = []
    pending_rows  = []

    with open(path, encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        has_vetted     = 'vetted'     in (reader.fieldnames or [])
        has_match_type = 'match_type' in (reader.fieldnames or [])
        for row in reader:
            basis = row.get('basis', '').strip()
            if not basis:
                continue
            vetted     = row.get('vetted',     '').strip() if has_vetted     else ''
            match_type = row.get('match_type', '').strip() if has_match_type else ''
            qid        = extract_qid(row.get('qid', ''))

            if vetted in ('Y', 'auto') and qid:
                vetted_rows.append(dict(row))
            elif match_type and match_type != 'llm_pending':
                if refresh and match_type == 'none':
                    pending_rows.append(dict(row))
                else:
                    resolved_rows.append(dict(row))
            else:
                pending_rows.append(dict(row))

    pending_rows.sort(key=lambda r: -int(r.get('freq', 0) or 0))
    return vetted_rows, resolved_rows, pending_rows


# ---------------------------------------------------------------------------
# HTTP session  (shared with generate_basis_seed.py)
# ---------------------------------------------------------------------------

_SESSION = requests.Session()
_SESSION.headers.update({'User-Agent': 'pb2wb-generate-basis/1.0'})

_RETRY_ADAPTER = requests.adapters.HTTPAdapter(
    max_retries=requests.packages.urllib3.util.retry.Retry(
        total=4,
        backoff_factor=2,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=['GET'],
    )
)
_SESSION.mount('https://', _RETRY_ADAPTER)
_SESSION.mount('http://',  _RETRY_ADAPTER)


# ---------------------------------------------------------------------------
# API search  (same pattern as fill_gaps.py)
# ---------------------------------------------------------------------------

def _normalize(s):
    """Lowercase + strip diacritics, for comparison only."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', s.lower())
        if unicodedata.category(c) != 'Mn'
    )


def _fetch_bibid_qids(qids):
    """
    Given a list of QIDs, return the subset that have a PhiloBiblon BIBID alias
    (BETA/BITAGAP/BITECA bibid <number>) in any language.
    Makes one wbgetentities call for all QIDs.
    Returns frozenset() on any network error.
    """
    if not qids:
        return frozenset()
    try:
        resp = _SESSION.get(FG['MEDIAWIKI_API_URL'], params={
            'action': 'wbgetentities',
            'ids': '|'.join(qids),
            'props': 'aliases',
            'format': 'json',
        }, timeout=15)
        resp.raise_for_status()
        entities = resp.json().get('entities', {})
        found = set()
        for qid, entity in entities.items():
            for lang_aliases in entity.get('aliases', {}).values():
                for alias in lang_aliases:
                    if _BIBID_RE.match(alias.get('value', '')):
                        found.add(qid)
                        break
        return frozenset(found)
    except requests.RequestException as e:
        print(f'\nWarning: wbgetentities error ({e}) — skipping BIBID disambiguation')
        return frozenset()


def _pick_best_result(results, value, ref_qids=frozenset()):
    """
    From a list of wbsearchentities results for *value*, return the best
    (qid, label, description, subtype) according to:
      1. Exact match (label or alias) whose QID is in ref_qids (has BIBID alias)
      2. Exact match whose description contains reference keywords
      3. First exact match (label or alias)
      4. First result as fuzzy
      5. Empty if no results

    ref_qids is a pre-fetched frozenset of QIDs known to be reference sources,
    obtained via _fetch_bibid_qids.  Pass frozenset() to skip this tier.
    """
    norm_value = _normalize(value)
    exact = []
    for r in results:
        mi = r.get('match', {})
        if mi.get('type') in ('label', 'alias') and _normalize(mi.get('text', '')) == norm_value:
            exact.append(r)

    def _unpack(r):
        mi = r.get('match', {})
        return r.get('id', ''), r.get('label', ''), r.get('description', ''), mi.get('type', '')

    if exact:
        # Prefer known reference-source items (BIBID alias confirmed)
        for r in exact:
            if r.get('id') in ref_qids:
                return _unpack(r)
        # Prefer reference-source description keywords
        for r in exact:
            if _REF_DESC_RE.search(r.get('description', '')):
                return _unpack(r)
        # Fall back to first exact match that isn't a disqualified type
        for r in exact:
            if not _REJECT_DESC_RE.search(r.get('description', '')):
                return _unpack(r)
        return '', '', '', ''   # all candidates were disqualified (family name, etc.)

    if results:
        r = results[0]
        qid = r.get('id', '')
        if qid:
            return qid, r.get('label', ''), r.get('description', ''), 'fuzzy'
    return '', '', '', ''


def api_search_one(value):
    """
    Search FactGrid via wbsearchentities.
    Returns (qid, label, description, subtype) where subtype is:
      'label'  — matched on primary label, text == value (exact)
      'alias'  — matched on an alias, text == value (exact)
      'fuzzy'  — API returned a hit but matched text differs from query
      ''       — no result

    Fetches up to 5 candidates. When multiple exact matches are found,
    makes a second wbgetentities call to check for PhiloBiblon BIBID aliases
    and prefers reference-source items over person/place items.
    """
    try:
        resp = _SESSION.get(FG['MEDIAWIKI_API_URL'], params={
            'action': 'wbsearchentities',
            'search': value,
            'language': 'en',
            'type': 'item',
            'limit': 5,
            'format': 'json',
        }, timeout=10)
        resp.raise_for_status()
        results = resp.json().get('search', [])
    except requests.RequestException as e:
        print(f'\nWarning: API error for {value!r}: {e}')
        return '', '', '', ''
    if not results:
        return '', '', '', ''

    norm_value = _normalize(value)
    exact_qids = [
        r['id'] for r in results
        if r.get('match', {}).get('type') in ('label', 'alias')
        and _normalize(r.get('match', {}).get('text', '')) == norm_value
    ]
    ref_qids = _fetch_bibid_qids(exact_qids) if len(exact_qids) > 1 else frozenset()
    return _pick_best_result(results, value, ref_qids)


# ---------------------------------------------------------------------------
# Anthropic API  (prompt caching on system prompt)
# ---------------------------------------------------------------------------

_ANTHROPIC_SYSTEM_PROMPT = """\
You are a citation parser for PhiloBiblon, a bibliography of medieval Iberian texts.

Each input is a raw P721 string — a source/basis citation that has already had HTML
tags stripped.  Your job is to split it into a searchable KEY and an optional LOCATOR.

Definitions:
  key  — the part that identifies the reference work, author, or institution.
          This is what will be searched in a bibliographic database.
  loc  — page number, folio, volume+page, or other locator.  Empty string if none.

Locator patterns (extract these into loc, remove from key):
  Plain page:      169  /  48-50  /  281, 283
  Volume+page:     I:48-50  /  XIV:3  /  4:286  (keep colon, keep together in loc)
  Folio:           93v  /  f. 3r  /  ff. 12v-13r
  Footnote:        27n  /  14n
  Year alone:      2004  (only when it appears after the key, separated by space,
                          and the key already contains a year — otherwise the year
                          is part of the key)

Conservative rules:
  - When in doubt, put the whole string in key and leave loc empty.
  - Shelfmarks (e.g. BNE MSS/7811, AHN Clero Aragón 2099) are keys, not locators.
  - Abbreviations (IGM, DHEE, ACA) are keys.
  - If the string looks like "Author YEAR" (already handled upstream), echo it unchanged.

Return exactly one JSON object and nothing else:
{"key": "...", "loc": "..."}

Examples:
"Faulhaber" → {"key": "Faulhaber", "loc": ""}
"BNE MSS/7811" → {"key": "BNE MSS/7811", "loc": ""}
"AHN Clero Aragón 2099" → {"key": "AHN Clero Aragón 2099", "loc": ""}
"Rodríguez x" → {"key": "Rodríguez", "loc": "x"}
"Gómez Moreno 1994:138-40" → {"key": "Gómez Moreno 1994", "loc": "138-40"}
"García de la Concha 1983" → {"key": "García de la Concha 1983", "loc": ""}
"Arxiu de la Corona d'Aragó" → {"key": "Arxiu de la Corona d'Aragó", "loc": ""}
"IGM" → {"key": "IGM", "loc": ""}
"""


def _make_anthropic_client():
    """Create Anthropic client. Requires ANTHROPIC_API_KEY env var."""
    try:
        import anthropic
        return anthropic.Anthropic()
    except (ImportError, Exception):
        return None


def anthropic_parse_citation(basis, client):
    """
    Parse an ambiguous P721 string using the Anthropic API with prompt caching.
    Returns {'key': str, 'loc': str, 'loc_type': str} or None on failure.
    """
    import json
    try:
        response = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=128,
            system=[{
                'type': 'text',
                'text': _ANTHROPIC_SYSTEM_PROMPT,
                'cache_control': {'type': 'ephemeral'},
            }],
            messages=[{'role': 'user', 'content': basis}],
        )
        text = response.content[0].text.strip()
        parsed = json.loads(text)
        key = parsed.get('key', '').strip()
        loc = parsed.get('loc', '').strip()
        if not key:
            return None
        return {'key': key, 'loc': loc, 'loc_type': detect_loc_type(loc)}
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def hyperlink(qid):
    """Wrap a QID in a Google Sheets HYPERLINK formula so it is clickable."""
    if not qid:
        return ''
    return f'=HYPERLINK("{_FG_WIKI_BASE}{qid}","{qid}")'


def vetted_value(match_type):
    """Initial vetted value for a freshly matched row.
    High-confidence matches get 'auto'; everything else is blank (needs review).
    """
    if match_type in ('api_label', 'api_alias'):
        return 'auto'
    return ''


def out_row(freq, basis, key, loc, loc_type, match_type, qid, label, vetted='',
            parse_pattern=''):
    return {
        'freq':       freq,
        'basis':      basis,
        'key':        key,
        'match_type': match_type,
        'qid':        hyperlink(qid),
        'label':      label,
        'vetted':     vetted,
        'loc':        loc,
        'loc_type':   loc_type,
        **parse_loc_columns(loc, loc_type, parse_pattern),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Search P721 basis strings from sheet and write candidates TSV')
    parser.add_argument('--sheet',   default=SHEET_TSV,
                        help=f'Input sheet TSV (default: {SHEET_TSV})')
    parser.add_argument('--out',     default=OUT_TSV,
                        help=f'Output candidates TSV (default: {OUT_TSV})')
    parser.add_argument('--limit',   type=int, default=0,
                        help='Process only the top N unvetted rows (for testing)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be searched without calling the API')
    parser.add_argument('--llm',     action='store_true',
                        help='Use Anthropic API to parse llm_pending rows')
    parser.add_argument('--refresh', action='store_true',
                        help='Re-search match_type=none rows (e.g. after new FactGrid items)')
    args = parser.parse_args()

    anthropic_client = None
    if args.llm:
        anthropic_client = _make_anthropic_client()
        if anthropic_client is None:
            print('Warning: Anthropic client unavailable — --llm has no effect.')

    print(f'Reading sheet:  {args.sheet}')
    vetted_rows, resolved_rows, pending_rows = load_sheet(args.sheet, refresh=args.refresh)
    print(f'  vetted   : {len(vetted_rows)}')
    print(f'  resolved : {len(resolved_rows)}')
    print(f'  pending  : {len(pending_rows)}')

    if args.limit:
        pending_rows = pending_rows[:args.limit]
        print(f'  (limited to top {args.limit} pending rows)')

    # --- Preprocess all pending rows upfront ---
    preprocessed = [(r, preprocess(r['basis'])) for r in pending_rows]
    excluded  = [(r, pp) for r, pp in preprocessed if pp['preproc_type'] == 'excluded']
    compound  = [(r, pp) for r, pp in preprocessed if pp['preproc_type'] == 'compound']
    to_search = [(r, pp) for r, pp in preprocessed if pp['preproc_type'] == '']

    pending = [(r, pp) for r, pp in to_search if pp['parse_pattern'] == 'raw']
    print(f'  excluded : {len(excluded)}  compound : {len(compound)}  '
          f'to search: {len(to_search)}  (llm_pending: {len(pending)})')

    # --- LLM pass: parse llm_pending rows into key + loc ---
    if args.llm and anthropic_client and pending:
        print(f'Running Anthropic on {len(pending)} pending rows...')
        llm_ok = llm_fail = 0
        with tqdm(pending, unit='row') as bar:
            for r, pp in bar:
                result = anthropic_parse_citation(pp['basis'], anthropic_client)
                if result:
                    pp['key']           = result['key']
                    pp['loc']           = result['loc']
                    pp['loc_type']      = result['loc_type']
                    pp['parse_pattern'] = 'llm'
                    llm_ok += 1
                else:
                    llm_fail += 1
                bar.set_postfix(ok=llm_ok, fail=llm_fail)
        print(f'  LLM parsed: {llm_ok}  failed/unchanged: {llm_fail}')

    if args.dry_run:
        for r, pp in to_search:
            print(f"  [{pp['parse_pattern']:14s}] key={pp['key']!r:35s}  "
                  f"loc={pp['loc']!r}  ({r.get('freq', '?')}×)")
        print('(dry-run: no API calls made, no output written)')
        return

    # --- Deduplicate keys, preserving frequency order ---
    seen_keys: set = set()
    unique_keys = []
    for _, pp in to_search:
        k = pp['key']
        if k not in seen_keys:
            seen_keys.add(k)
            unique_keys.append(k)
    print(f'  unique keys: {len(unique_keys)}  '
          f'(dedup saves {len(to_search) - len(unique_keys)} API calls)')

    # --- API lookup: one call per unique key ---
    key_map: dict = {}
    matched = 0
    with tqdm(unique_keys, unit='key') as bar:
        for key in bar:
            qid, label, _, subtype = api_search_one(key)
            if qid:
                mtype = f'api_{subtype}' if subtype in ('label', 'alias') else 'api_fuzzy'
                matched += 1
            else:
                qid = label = mtype = ''
            key_map[key] = (qid, label, mtype)
            bar.set_postfix(matched=matched)

    # --- Assemble output rows ---
    out_rows = []

    for r in vetted_rows:
        out_rows.append(out_row(
            r.get('freq', ''), r['basis'],
            r.get('key', ''), r.get('loc', ''), r.get('loc_type', ''),
            'vetted',
            extract_qid(r.get('qid', '')),
            r.get('label', ''),
            vetted=r.get('vetted', 'Y'),
            parse_pattern=r.get('parse_pattern', ''),
        ))
    for r in resolved_rows:
        out_rows.append(out_row(
            r.get('freq', ''), r['basis'],
            r.get('key', ''), r.get('loc', ''), r.get('loc_type', ''),
            r.get('match_type', ''),
            extract_qid(r.get('qid', '')),
            r.get('label', ''),
            vetted=r.get('vetted', ''),
            parse_pattern=r.get('parse_pattern', ''),
        ))
    for r, pp in excluded:
        out_rows.append(out_row(r.get('freq', ''), pp['basis'], pp['key'],
                                pp['loc'], pp['loc_type'], 'excluded', '', '',
                                parse_pattern=pp['parse_pattern']))
    for r, pp in compound:
        out_rows.append(out_row(r.get('freq', ''), pp['basis'], pp['key'],
                                pp['loc'], pp['loc_type'], 'compound', '', '',
                                parse_pattern=pp['parse_pattern']))
    for r, pp in to_search:
        qid, label, mtype = key_map.get(pp['key'], ('', '', ''))
        if not qid and not mtype:
            if pp['parse_pattern'] == 'raw':
                mtype = 'llm_pending'
            elif pp['parse_pattern'] == 'shelfmark':
                mtype = 'shelfmark'
            else:
                mtype = 'none'
        out_rows.append(out_row(r.get('freq', ''), pp['basis'], pp['key'],
                                pp['loc'], pp['loc_type'], mtype, qid, label,
                                vetted=vetted_value(mtype),
                                parse_pattern=pp['parse_pattern']))

    out_rows.sort(key=lambda r: -(int(r['freq']) if str(r['freq']).isdigit() else 0))

    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    with open(args.out, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=OUT_COLUMNS, delimiter='\t')
        writer.writeheader()
        writer.writerows(out_rows)

    from collections import Counter
    mc = Counter(r['match_type'] for r in out_rows)
    print(f'\nWritten: {args.out}  ({len(out_rows)} rows)')
    print(f'  vetted      : {mc["vetted"]}')
    print(f'  excluded    : {mc["excluded"]}')
    print(f'  compound    : {mc["compound"]}')
    print(f'  api_label   : {mc["api_label"]}')
    print(f'  api_alias   : {mc["api_alias"]}')
    print(f'  api_fuzzy   : {mc["api_fuzzy"]}')
    print(f'  none        : {mc["none"]}')
    print(f'  llm_pending : {mc["llm_pending"]}')


if __name__ == '__main__':
    main()
