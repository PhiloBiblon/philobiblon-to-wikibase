"""
generate_basis_mapping.py — iterative search pass for P721 basis/reference migration.

Reads the pulled Google Sheet TSV (P721-P129.tsv), re-processes all rows where
vetted is blank, and writes a candidates TSV for review/merge.

Rows already marked vetted (Y) are passed through unchanged.
Rows where vetted is blank are re-preprocessed from the basis string and
re-searched via the wbsearchentities API.  This means Charles's or Max's
corrections to the basis column are automatically picked up on re-run.

Pre-processing pipeline (applied in order after HTML stripping):
  excluded      — non-reference strings (fol. mod., ?, princeps, etc.)
  compound      — contains ' / '; skip search, flag for manual handling
  dhee          — "DHEE <loc>" → key=DHEE, loc=<loc>
  auth_year_loc — "Author 1997:60" → key="Author 1997", loc="60"
  roman_vol     — "Author I:286" → key="Author", loc="I:286"
  roman_lower   — "Azáceta xxii" → key="Azáceta", loc="xxii"
  auth_year     — "Author 2006" → key="Author 2006", loc=""
  raw           — no pattern matched; key = whole string

loc_type is inferred from the loc component (or returned directly by the LLM):
  page      — plain page number or range
  folio     — e.g. "93v", "f. 3r"
  footnote  — e.g. "27n"
  volume    — roman numeral or volume:page reference
  annotation — catalog annotation term (ex-libris, sello); key=catalog prefix, loc=term
  llm_guess — LLM saw something locator-like but could not classify it
  ''        — no locator

match_type values in output:
  vetted       — row was already vetted (Y) in the sheet; passed through
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

import hashlib
import os
import sys
import re
import csv
import argparse
import time
import unicodedata

dir_path = os.path.dirname(os.path.realpath(__file__))
parent_dir_path = os.path.dirname(dir_path)
sys.path.append(parent_dir_path)

import requests
from tqdm import tqdm
from common.settings import BASE_IMPORT_OBJECTS

FG = BASE_IMPORT_OBJECTS['FACTGRID']

SHEET_TSV   = 'prop_migration/P721-P129.tsv'
OUT_TSV     = 'prop_migration/basis_candidates.tsv'
KNOWN_QIDS  = 'prop_migration/known_qids.tsv'
_LLM_CKPT_DIR = 'prop_migration'
API_CKPT      = 'prop_migration/.api_ckpt.tsv'


def _llm_ckpt_paths(model):
    """Return (tsv_path, meta_path) for the given model+prompt combination.

    Both model name and a short prompt hash are embedded in the filename so
    that changing either produces a new, separate cache file.
    """
    slug  = re.sub(r'[^a-zA-Z0-9._-]', '-', model.split('/')[-1])
    phash = _cache_key(model)[:6]
    base  = f'{_LLM_CKPT_DIR}/.llm_ckpt.{slug}.{phash}'
    return base + '.tsv', base + '.meta'

OUT_COLUMNS = [
    'freq', 'basis', 'key',
    'match_type', 'qid', 'label', 'vetted',
    'loc_type', 'loc',
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
    # Catalan equivalent of fol. mod.
    'paginació moderna',
}

# Regex patterns for exclusion — applied case-insensitively after strip_html.
# Covers families of variants too broad for exact matching.
EXCLUDED_PATTERNS = [
    re.compile(r'^wikidata\s*\(',  re.IGNORECASE),  # Wikidata (2012-) and similar dated variants
    re.compile(r'^wikipedia\s+en\b', re.IGNORECASE),  # Wikipedia en español, Wikipedia en català, …
    re.compile(r'\bfichero\b',  re.IGNORECASE),  # fichero, fichero de Palacio, BNE fichero, …
    re.compile(r'^https?://',   re.IGNORECASE),  # bare URLs
    re.compile(r'^f{1,2}\.\s*\d+\s*[rv]', re.IGNORECASE),  # folio refs used as basis: f. 1r, ff. 3v…
]

# Compound references: two sources separated by " / "
COMPOUND_RE = re.compile(r'\s/\s')

# Catalog annotations: "PREFIX: TERM" where TERM is a known annotation word.
# Examples: "BNE Cat.: sello", "BNE Cat.: ex-libris", "IBIS: ex-libris"
# key → catalog prefix (looked up for P129 QID), loc → annotation term (P700 qualifier)
_ANNOTATION_TERMS = frozenset({
    'ex-libris', 'ex libris', 'ex-libris ms', 'ex-libris mss',
    'sello', 'sellos', 'timbre',
})
# QIDs for P700 qualifier values (annotation term → QID)
ANNOTATION_QIDS = {
    'ex-libris':     'Q418813',
    'ex libris':     'Q418813',
    'ex-libris ms':  'Q418813',
    'ex-libris mss': 'Q418813',
    'sello':         'Q394152',
    'sellos':        'Q394152',
}
_COLON_SPLIT_RE = re.compile(r'^(.+?)\s*:\s*(.+)$')

def _catalog_annotation_split(basis):
    """Return (prefix, annotation) if basis is 'PREFIX: known-term', else None."""
    m = _COLON_SPLIT_RE.match(basis)
    if not m:
        return None
    annotation = m.group(2).strip().lower()
    if annotation in _ANNOTATION_TERMS:
        return m.group(1).strip(), annotation
    return None

# Shelfmarks: slash not surrounded by spaces (e.g. BNE MSS/7811, Frankfurt a/M: …)
SHELFMARK_RE = re.compile(r'(?<! )/|/(?! )')

# BNM / bare-BNE shelfmarks → normalise to BNE MSS/ or BNE R/ canonical form.
# Examples: BNM 12688 → BNE MSS/12688, BNM R 4277 → BNE R/4277,
#           BNM Res. 151 → BNE Res./151, BNE 11277 → BNE MSS/11277
# An optional trailing locator (folio, page) is captured separately.
_BNM_RE = re.compile(
    r'^(?:BNM|BNE)\s+'                     # prefix
    r'(R|Res\.|MS|MSS|I)?\s*'              # optional section code
    r'(\d[\d/]*(?:\.\d+)?)'                # shelfmark number (may include /)
    r'(?:\s+(.+))?$',                       # optional trailing locator
    re.IGNORECASE,
)

def _bnm_normalise(basis):
    """
    Return (key, loc, loc_type) for a BNM/BNE shelfmark string, or None if no match.
    Normalises BNM → BNE and adds MSS/ where no section code is present.
    """
    m = _BNM_RE.match(basis)
    if not m:
        return None
    section = (m.group(1) or '').upper().rstrip('.')
    number  = m.group(2)
    trailer = (m.group(3) or '').strip()

    if section in ('R',):
        key = f'BNE R/{number}'
    elif section in ('RES', 'RES.'):
        key = f'BNE Res./{number}'
    elif section in ('MS', 'MSS'):
        key = f'BNE MSS/{number}'
    elif section == 'I':
        key = f'BNE {section}/{number}'
    else:
        key = f'BNE MSS/{number}'

    loc      = trailer
    loc_type = detect_loc_type(loc)
    return key, loc, loc_type

# DHEE followed by a locator (looks like a year but is a page number)
DHEE_RE = re.compile(r'^DHEE\s+(\S+)\s*$', re.IGNORECASE)

# Author + 4-digit year + colon + locator  e.g. "Beltrán 1997:60"
AUTH_YEAR_LOC_RE = re.compile(r'^(.+?\s+\d{4}):(.+)$')

# Roman-numeral volume + arabic page  e.g. "Arteaga I:286"
# Requires at least one uppercase Roman-numeral letter before the colon.
ROMAN_VOL_RE = re.compile(r'^(.+?)\s+([IVXLCDM]+:\d+\S*)\s*$')

# Lowercase roman-numeral locator at end, no colon  e.g. "Azáceta xxii", "Penna ciii"
# The last token must consist entirely of lowercase roman-numeral characters.
# Placed after ROMAN_VOL_RE (uppercase+colon takes priority).
ROMAN_LOWER_RE = re.compile(r'^(.+?)\s+([ivxlcdm]+)$')

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

# Trailing plain year (not already in parens) for auth_year fallback search
_AUTH_YEAR_TAIL_RE = re.compile(r'^(.+?)\s+(\d{4}(?:-\d{2,4})?)$')

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
    """
    Infer the type of a locator string.

    Returns one of: 'folio', 'footnote', 'volume', 'page', or '' (no locator).
    'llm_guess' is also a valid value, set by the LLM when uncertain.
    """
    if not loc:
        return ''
    if FOOTNOTE_LOC_RE.match(loc):
        return 'footnote'
    if FOLIO_LOC_RE.match(loc):
        return 'folio'
    if _VOL_PAGE_RE.match(loc):
        return 'volume'
    return 'page'


def preprocess(raw):
    """
    Strip HTML, classify, and parse key/loc/loc_type from a raw P721 string.

    Returns a dict:
      basis         — HTML-stripped string
      key           — searchable component (sent to wbsearchentities)
      loc           — locator/page component
      loc_type      — '', 'page', 'folio', 'footnote', 'volume', 'llm_guess'
      preproc_type  — '', 'excluded', 'compound'
      parse_pattern — rule that fired: 'bnm_norm', 'catalog_annotation', 'dhee',
                      'auth_year_loc', 'roman_vol', 'roman_lower', 'auth_year', 'raw'
    """
    basis = strip_html(raw)

    if is_excluded(basis):
        return _pp(basis, basis, '', '', 'excluded', 'raw')

    if COMPOUND_RE.search(basis):
        return _pp(basis, basis, '', '', 'compound', 'raw')

    bnm = _bnm_normalise(basis)
    if bnm:
        key, loc, loc_type = bnm
        return _pp(basis, key, loc, loc_type, '', 'bnm_norm')

    ann = _catalog_annotation_split(basis)
    if ann:
        prefix, annotation = ann
        return _pp(basis, prefix, annotation, 'annotation', '', 'catalog_annotation')

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

    m = ROMAN_LOWER_RE.match(basis)
    if m:
        key = m.group(1).strip()
        loc = m.group(2).strip()
        return _pp(basis, key, loc, detect_loc_type(loc), '', 'roman_lower')

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

      vetted_rows   — vetted=Y with qid; output as match_type='vetted'
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

            if vetted == 'Y' and qid:
                vetted_rows.append(dict(row))
            elif match_type and match_type not in ('llm_pending', 'compound', 'legacy'):
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


def _auth_year_paren_form(key):
    """
    Convert 'Author YYYY' or 'Author YYYY-YY' to 'Author (YYYY)' / 'Author (YYYY-YY)'.
    Returns None if year is already parenthesised or pattern doesn't match.
    """
    m = _AUTH_YEAR_TAIL_RE.match(key)
    return f'{m.group(1)} ({m.group(2)})' if m else None


def _wbsearch(value):
    """Raw wbsearchentities call. Returns list of results or [] on error."""
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
        return resp.json().get('search', [])
    except requests.RequestException as e:
        print(f'\nWarning: API error for {value!r}: {e}')
        return []


def api_search_one(value, parse_pattern=''):
    """
    Search FactGrid via wbsearchentities.
    Returns (qid, label, description, subtype) where subtype is:
      'label'  — exact label match
      'alias'  — exact alias match
      'fuzzy'  — API hit but matched text differs from query
      ''       — no result

    For auth_year keys (e.g. 'Norton 1978') that return no exact match,
    retries with parenthesised year form ('Norton (1978)') since many FG
    items have labels like 'Norton (1978), A Descriptive Catalogue...'.
    """
    results = _wbsearch(value)
    if results:
        norm_value = _normalize(value)
        exact_qids = [
            r['id'] for r in results
            if r.get('match', {}).get('type') in ('label', 'alias')
            and _normalize(r.get('match', {}).get('text', '')) == norm_value
        ]
        ref_qids = _fetch_bibid_qids(exact_qids) if len(exact_qids) > 1 else frozenset()
        qid, label, desc, subtype = _pick_best_result(results, value, ref_qids)
        if qid:
            return qid, label, desc, subtype

    if parse_pattern in ('auth_year', 'llm', 'raw'):
        # Fallback 1: retry with year in parentheses e.g. "Norton (1978)"
        paren = _auth_year_paren_form(value)
        if paren:
            fb_results = _wbsearch(paren)
            if fb_results:
                qid, label, desc, _ = _pick_best_result(fb_results, paren)
                if qid:
                    return qid, label, desc, 'fuzzy'

        # Fallback 2: search author name only, filter results containing (YYYY)
        # Handles compound surnames: "Sáez 2002" → search "Sáez", filter "(2002)"
        m = _AUTH_YEAR_TAIL_RE.match(value)
        if m:
            author, year = m.group(1), m.group(2)[:4]
            author_results = _wbsearch(author)
            year_paren = f'({year})'
            year_matches = [
                r for r in author_results
                if year_paren in r.get('label', '')
                and not _REJECT_DESC_RE.search(r.get('description', ''))
            ]
            if year_matches:
                r = year_matches[0]
                return r.get('id', ''), r.get('label', ''), r.get('description', ''), 'fuzzy'

    return '', '', '', ''


# ---------------------------------------------------------------------------
# Anthropic API  (prompt caching on system prompt)
# ---------------------------------------------------------------------------

_LLM_SYSTEM_PROMPT = """\
You are a citation parser for PhiloBiblon, a bibliography of medieval Iberian texts.

Each input is a raw P721 string — a source/basis citation that has already had HTML
tags stripped.  Your job is to split it into a searchable KEY, an optional LOCATOR,
and a LOCATOR TYPE.

These strings have already been tested against standard patterns (Author YEAR,
Author YEAR:LOC, Roman-volume:page, DHEE locator) and did not match.  Treat them
conservatively — most should have loc="" and loc_type="".

Definitions:
  key      — the part that identifies the reference work, author, or institution.
              This is what will be searched in a bibliographic database.
  loc      — page number, folio, volume+page, or other locator.  Empty string if none.
  loc_type — one of: "page", "folio", "footnote", "volume", "llm_guess", or "".
             Use "" when loc is empty.
             Use "llm_guess" when you see something that looks like a locator but
             you cannot confidently classify it as page, folio, footnote, or volume.

Locator types:
  page:     169  /  48-50  /  281, 283  /  138-40
  volume:   I:48-50  /  XIV:3  /  4:286  /  x  /  xxii  /  VII:492
            (roman numerals alone, or roman/arabic with colon)
  folio:    93v  /  f. 3r  /  ff. 12v-13r  /  244v
            (digits followed by r or v, optionally preceded by f. or ff.)
  footnote: 27n  /  14n  /  218n
            (digits followed by n)

Conservative rules:
  - When in doubt, put the whole string in key and leave loc and loc_type empty.
  - Shelfmarks and library call numbers are always keys, not locators
    (e.g. BNE MSS/7811, AHN Clero Aragón 2099, BNM 12688, esc. h.I.14).
  - Abbreviations and database names (IGM, DHEE, IBIS, PARES) are keys.
  - Institution names, catalog titles, and multi-word proper names are keys.
  - A colon in a string does NOT always mean key:locator — it may be part of
    a city:institution pattern or a descriptive qualifier; keep the whole string
    as the key unless there is a clear numeric locator after the colon.

Return exactly one JSON object and nothing else:
{"key": "...", "loc": "...", "loc_type": "..."}

Examples:
"Faulhaber" → {"key": "Faulhaber", "loc": "", "loc_type": ""}
"BNE MSS/7811" → {"key": "BNE MSS/7811", "loc": "", "loc_type": ""}
"BNM 12688" → {"key": "BNM 12688", "loc": "", "loc_type": ""}
"AHN Clero Aragón 2099" → {"key": "AHN Clero Aragón 2099", "loc": "", "loc_type": ""}
"Frankfurt: UB, lat. oct. 231" → {"key": "Frankfurt: UB, lat. oct. 231", "loc": "", "loc_type": ""}
"BNE Cat.: sello" → {"key": "BNE Cat.: sello", "loc": "", "loc_type": ""}
"Gómez Moreno 1994:138-40" → {"key": "Gómez Moreno 1994", "loc": "138-40", "loc_type": "page"}
"García de la Concha 1983" → {"key": "García de la Concha 1983", "loc": "", "loc_type": ""}
"Beltrán 1997:27n" → {"key": "Beltrán 1997", "loc": "27n", "loc_type": "footnote"}
"Simó 1998:74n" → {"key": "Simó 1998", "loc": "74n", "loc_type": "footnote"}
"RB II/86 f. 93v" → {"key": "RB II/86", "loc": "f. 93v", "loc_type": "folio"}
"Egerton 292:3r" → {"key": "Egerton 292", "loc": "3r", "loc_type": "folio"}
"Rodríguez x" → {"key": "Rodríguez", "loc": "x", "loc_type": "volume"}
"Azáceta xxii" → {"key": "Azáceta", "loc": "xxii", "loc_type": "volume"}
"Dutton 1991 7:492" → {"key": "Dutton 1991", "loc": "VII:492", "loc_type": "volume"}
"Lilao et al." → {"key": "Lilao et al.", "loc": "", "loc_type": ""}
"Arxiu de la Corona d'Aragó" → {"key": "Arxiu de la Corona d'Aragó", "loc": "", "loc_type": ""}
"IGM" → {"key": "IGM", "loc": "", "loc_type": ""}
"Morel-Fatio" → {"key": "Morel-Fatio", "loc": "", "loc_type": ""}
"Alvar & Lucía" → {"key": "Alvar & Lucía", "loc": "", "loc_type": ""}
"RBME Cat." → {"key": "RBME Cat.", "loc": "", "loc_type": ""}
"BnF Espagnol 80" → {"key": "BnF Espagnol 80", "loc": "", "loc_type": ""}
"RAE MS. 68" → {"key": "RAE MS. 68", "loc": "", "loc_type": ""}
"Índice Salazar y Castro" → {"key": "Índice Salazar y Castro", "loc": "", "loc_type": ""}
"Llull DB" → {"key": "Llull DB", "loc": "", "loc_type": ""}
"Ms. Zabálburu" → {"key": "Ms. Zabálburu", "loc": "", "loc_type": ""}
"BETA bibid 1234" → {"key": "BETA bibid 1234", "loc": "", "loc_type": ""}
"Avenoza 2001:24n" → {"key": "Avenoza 2001", "loc": "24n", "loc_type": "footnote"}
"Aragüés 2008" → {"key": "Aragüés 2008", "loc": "", "loc_type": ""}
"Villacorta 2005" → {"key": "Villacorta 2005", "loc": "", "loc_type": ""}
"Accorsi 2011" → {"key": "Accorsi 2011", "loc": "", "loc_type": ""}
"Fernández 1901" → {"key": "Fernández 1901", "loc": "", "loc_type": ""}
"García & Gonzálvez 1970" → {"key": "García & Gonzálvez 1970", "loc": "", "loc_type": ""}
"Lilao et al." → {"key": "Lilao et al.", "loc": "", "loc_type": ""}
"Álvarez & Crespí" → {"key": "Álvarez & Crespí", "loc": "", "loc_type": ""}
"Beceiro Pita & Franco Silva 1985:292" → {"key": "Beceiro Pita & Franco Silva 1985", "loc": "292", "loc_type": "page"}
"Fradejas 2023" → {"key": "Fradejas 2023", "loc": "", "loc_type": ""}
"Haro ed. 1998" → {"key": "Haro ed. 1998", "loc": "", "loc_type": ""}
"RAH Cat." → {"key": "RAH Cat.", "loc": "", "loc_type": ""}
"Huntington Cat." → {"key": "Huntington Cat.", "loc": "", "loc_type": ""}
"BnF Cat." → {"key": "BnF Cat.", "loc": "", "loc_type": ""}
"BU Salamanca Cat." → {"key": "BU Salamanca Cat.", "loc": "", "loc_type": ""}
"RAE Cat." → {"key": "RAE Cat.", "loc": "", "loc_type": ""}
"BNP Cat." → {"key": "BNP Cat.", "loc": "", "loc_type": ""}
"Newton Cat." → {"key": "Newton Cat.", "loc": "", "loc_type": ""}
"BCol. Cat." → {"key": "BCol. Cat.", "loc": "", "loc_type": ""}
"PARES" → {"key": "PARES", "loc": "", "loc_type": ""}
"Digital Scriptorium" → {"key": "Digital Scriptorium", "loc": "", "loc_type": ""}
"Manuscripta Medievalia" → {"key": "Manuscripta Medievalia", "loc": "", "loc_type": ""}
"Manuscriptorium" → {"key": "Manuscriptorium", "loc": "", "loc_type": ""}
"GENi" → {"key": "GENi", "loc": "", "loc_type": ""}
"National Library of Wales" → {"key": "National Library of Wales", "loc": "", "loc_type": ""}
"Bibl. de Catalunya" → {"key": "Bibl. de Catalunya", "loc": "", "loc_type": ""}
"BNE Inv. topográfico provisional" → {"key": "BNE Inv. topográfico provisional", "loc": "", "loc_type": ""}
"Ex Bibliotheca Gondomariensi" → {"key": "Ex Bibliotheca Gondomariensi", "loc": "", "loc_type": ""}
"Compilación A" → {"key": "Compilación A", "loc": "", "loc_type": ""}
"ed. Sevilla, 1520" → {"key": "ed. Sevilla, 1520", "loc": "", "loc_type": ""}
"Santander BMyP 169 (8)" → {"key": "Santander BMyP 169 (8)", "loc": "", "loc_type": ""}
"B Catalunya 1225" → {"key": "B Catalunya 1225", "loc": "", "loc_type": ""}
"RAH 9-28-3/5495" → {"key": "RAH 9-28-3/5495", "loc": "", "loc_type": ""}
"Ureña y Bonilla" → {"key": "Ureña y Bonilla", "loc": "", "loc_type": ""}
"Fernández-Ordóñez 2000" → {"key": "Fernández-Ordóñez 2000", "loc": "", "loc_type": ""}
"Mangas 2020 \"Transmisión\"" → {"key": "Mangas 2020 \"Transmisión\"", "loc": "", "loc_type": ""}
"Puerto Moro 2008" → {"key": "Puerto Moro 2008", "loc": "", "loc_type": ""}
"Carriazo 1943" → {"key": "Carriazo 1943", "loc": "", "loc_type": ""}
"Sáez" → {"key": "Sáez", "loc": "", "loc_type": ""}
"Kraus" → {"key": "Kraus", "loc": "", "loc_type": ""}
"Capuano" → {"key": "Capuano", "loc": "", "loc_type": ""}
"von Euw & Plotzek" → {"key": "von Euw & Plotzek", "loc": "", "loc_type": ""}
"Martín Abad 1994 [1998]" → {"key": "Martín Abad 1994 [1998]", "loc": "", "loc_type": ""}
"""


def _load_env():
    for fname in ('.qs_env', '.env'):
        if os.path.exists(fname):
            with open(fname) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        os.environ.setdefault(k.strip(), v.strip())
            return


_DEFAULT_LLM_MODEL = 'anthropic/claude-sonnet-4-6'

# Map litellm model prefix → env var that must be set.
# litellm reads these automatically once they're in the environment.
_MODEL_KEY_ENV = {
    'gemini/':     'GEMINI_API_KEY',
    'anthropic/':  'ANTHROPIC_API_KEY',
    'ollama/':     None,   # no key needed for local Ollama
}


def _check_llm_env(model):
    """Load .qs_env and verify the required API key is present. Exits on failure."""
    _load_env()
    if model.startswith('anthropic/') and 'haiku' in model.lower():
        print(f'Warning: prompt caching will not work with {model!r} — Haiku requires '
              f'≥4,096 tokens to cache but this prompt is ~{len(_LLM_SYSTEM_PROMPT)//4} tokens. '
              f'Use anthropic/claude-sonnet-4-6 instead.')
    for prefix, env_var in _MODEL_KEY_ENV.items():
        if model.startswith(prefix):
            if env_var and not os.environ.get(env_var):
                sys.exit(f'Fatal: {env_var} not set — required for model {model!r}.\n'
                         f'Add it to .qs_env.')
            return
    # Unknown prefix — let litellm handle it; just load env.


def parse_citation(basis, model):
    """
    Parse an ambiguous P721 string via litellm.
    Returns {'key': str, 'loc': str, 'loc_type': str} or None on transient failure.
    Raises SystemExit on fatal auth/credit errors so the run aborts immediately.

    Supports any litellm model string, e.g.:
      gemini/gemini-2.0-flash
      anthropic/claude-haiku-4-5-20251001
      ollama/llama3
    """
    import json

    try:
        if model.startswith('anthropic/'):
            import anthropic as _anthropic
            model_id = model.split('/', 1)[1]
            client = _anthropic.Anthropic()
            response = client.messages.create(
                model=model_id,
                max_tokens=256,
                system=[{
                    'type': 'text',
                    'text': _LLM_SYSTEM_PROMPT,
                    'cache_control': {'type': 'ephemeral'},
                }],
                messages=[{'role': 'user', 'content': basis}],
            )
            text = response.content[0].text.strip()
        else:
            import litellm
            litellm.suppress_debug_info = True
            response = litellm.completion(
                model=model,
                messages=[
                    {'role': 'system', 'content': _LLM_SYSTEM_PROMPT},
                    {'role': 'user',   'content': basis},
                ],
                max_tokens=256,
            )
            text = response.choices[0].message.content.strip()
        text = re.sub(r'^```[a-z]*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
        parsed, _ = json.JSONDecoder().raw_decode(text)
        key      = parsed.get('key', '').strip()
        loc      = parsed.get('loc', '').strip()
        loc_type = parsed.get('loc_type', '').strip() or detect_loc_type(loc)
        if not key:
            return None
        return {'key': key, 'loc': loc, 'loc_type': loc_type}
    except Exception as e:
        if 'auth' in type(e).__name__.lower() or 'authentication' in str(e).lower():
            sys.exit(f'\nFatal LLM auth error ({model}): {e}\nCheck your API key.')
        raise   # let parse_citation_with_retry see the real error


def parse_citation_with_retry(basis, model, max_retries=6, initial_backoff=2):
    """
    Call parse_citation() with exponential backoff on rate-limit errors (429).
    Returns the result dict or None on persistent failure.
    """
    backoff = initial_backoff
    for attempt in range(max_retries):
        try:
            return parse_citation(basis, model)
        except Exception as e:
            is_rate_limit = ('429' in str(e) or 'rate' in str(e).lower()
                             or 'quota' in str(e).lower())
            tqdm.write(f'  LLM {"rate-limit" if is_rate_limit else "error"} '
                       f'(attempt {attempt+1}/{max_retries}, {type(e).__name__}): '
                       f'{str(e)[:200]}')
            if is_rate_limit and attempt < max_retries - 1:
                tqdm.write(f'  Retrying in {backoff}s...')
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
                continue
            return None
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
    return 'Y' if match_type in ('vetted', 'known') else ''


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
    }


# ---------------------------------------------------------------------------
# Checkpointing helpers
# ---------------------------------------------------------------------------

def _cache_key(model):
    """Short hash combining model name + system prompt — detects stale LLM caches."""
    payload = f'{model}\n{_LLM_SYSTEM_PROMPT}'.encode()
    return hashlib.sha256(payload).hexdigest()[:12]


def _load_llm_ckpt(path, model, meta_path=None):
    """
    Load LLM parse results.  Returns dict {basis: {key, loc, loc_type}}.

    If the meta sidecar doesn't match (model or prompt changed), the cache
    is considered stale and an empty dict is returned with a warning.
    """
    import json as _json
    if meta_path is None:
        _, meta_path = _llm_ckpt_paths(model)
    cache = {}
    if not os.path.exists(path):
        return cache
    if not os.path.exists(meta_path):
        print(f'  WARNING: LLM checkpoint has no meta sidecar — loading anyway.')
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            cache[row['basis']] = row
    return cache


def _write_llm_ckpt_meta(model, meta_path=None):
    """Write human-readable metadata sidecar for the LLM checkpoint."""
    import json as _json
    if meta_path is None:
        _, meta_path = _llm_ckpt_paths(model)
    meta = {
        'model':          model,
        'cache_key':      _cache_key(model),
        'prompt_preview': _LLM_SYSTEM_PROMPT[:120].replace('\n', ' '),
    }
    with open(meta_path, 'w') as f:
        _json.dump(meta, f, indent=2)


def _load_api_ckpt(path):
    """Load API search results. Returns dict {key: (qid, label, mtype)}."""
    cache = {}
    if not os.path.exists(path):
        return cache
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            cache[row['key']] = (row['qid'], row['label'], row['mtype'])
    return cache



def _load_known_qids(path=KNOWN_QIDS):
    """
    Load manually curated key → QID mappings for cases the API search misses.
    Returns dict {key: (qid, label, 'known')}.
    Missing file is silently ignored.
    """
    known = {}
    if not os.path.exists(path):
        return known
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            key   = row.get('key',   '').strip()
            qid   = row.get('qid',   '').strip()
            label = row.get('label', '').strip()
            if key and qid:
                known[key] = (qid, label, 'known')
    return known


def _promote_vetted_keys(key_corrections, path=KNOWN_QIDS):
    """
    Return merged dict {key: (qid, label, match_type)} combining known_qids.tsv
    with in-memory vetted key corrections.

    Vetted keys are NOT written to known_qids.tsv — that file is reserved for
    deliberately curated entries. Vetted keys propagate in-memory only, so that
    unvetted rows sharing the same key get the same QID within a single run.
    """
    existing = _load_known_qids(path)
    merged = dict(existing)
    for key, (qid, label) in key_corrections.items():
        if key not in merged:
            merged[key] = (qid, label, 'key_vetted')
    return merged


def _build_key_corrections(vetted_rows):
    """
    Build a key → (qid, label) map from vetted sheet rows.

    If two vetted rows share the same key but map to different QIDs, both are
    excluded and a warning is printed — the conflict must be resolved manually.

    Returns dict {key: (qid, label)}.
    """
    seen    = {}   # key → (qid, label) from first occurrence
    conflicts = set()
    for r in vetted_rows:
        key   = r.get('key',   '').strip()
        qid   = extract_qid(r.get('qid', ''))
        label = r.get('label', '').strip()
        if not key or not qid:
            continue
        if key in seen:
            if seen[key][0] != qid:
                conflicts.add(key)
        else:
            seen[key] = (qid, label)
    for key in conflicts:
        del seen[key]
        print(f'  WARNING: conflicting QIDs for key {key!r} — excluded from key propagation')
    return seen


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
                        help='Use LLM to parse llm_pending rows')
    parser.add_argument('--llm-model', default=_DEFAULT_LLM_MODEL,
                        help=f'litellm model string (default: {_DEFAULT_LLM_MODEL}). '
                             f'Examples: gemini/gemini-2.0-flash, '
                             f'anthropic/claude-haiku-4-5-20251001, ollama/llama3')
    parser.add_argument('--llm-delay', type=float, default=1.5,
                        help='Seconds to sleep between LLM calls (default: 1.5)')
    parser.add_argument('--refresh', action='store_true',
                        help='Re-search match_type=none rows (e.g. after new FactGrid items)')
    parser.add_argument('--clear-cache', action='store_true',
                        help='Delete LLM and API checkpoints and start fresh')
    parser.add_argument('--api-limit', type=int, default=0,
                        help='Search only the top N unique keys (by frequency); useful for iterative runs')
    args = parser.parse_args()

    if args.clear_cache:
        llm_ckpt, llm_meta = _llm_ckpt_paths(args.llm_model)
        for p in (llm_ckpt, llm_meta, API_CKPT):
            if os.path.exists(p):
                os.remove(p)
                print(f'Deleted cache: {p}')


    if args.llm:
        _check_llm_env(args.llm_model)
        print(f'LLM model: {args.llm_model}')

    print(f'Reading sheet:  {args.sheet}')
    vetted_rows, resolved_rows, pending_rows = load_sheet(args.sheet, refresh=args.refresh)
    print(f'  vetted   : {len(vetted_rows)}')
    print(f'  resolved : {len(resolved_rows)}')
    print(f'  pending  : {len(pending_rows)}')

    key_corrections = _build_key_corrections(vetted_rows)
    if key_corrections:
        print(f'  key corrections from vetted rows: {len(key_corrections)}')

    if args.limit:
        pending_rows = pending_rows[:args.limit]
        print(f'  (limited to top {args.limit} pending rows)')

    # --- Preprocess all pending rows upfront ---
    preprocessed = []
    for r in pending_rows:
        basis = r.get('basis', '').strip()
        pp = preprocess(basis)
        preprocessed.append((r, pp))
    excluded     = [(r, pp) for r, pp in preprocessed if pp['preproc_type'] == 'excluded']
    compound_raw = [(r, pp) for r, pp in preprocessed if pp['preproc_type'] == 'compound']
    to_search    = [(r, pp) for r, pp in preprocessed if pp['preproc_type'] == '']

    # Expand compound rows: split on ' / ', search each part separately.
    # Emit one output row per part (same basis, different key) so gsheets
    # compound-group logic inserts the extra sheet rows automatically.
    compound_parts = []  # (orig_row, orig_basis, part_pp)
    for r, pp in compound_raw:
        parts = [p.strip() for p in pp['basis'].split(' / ')]
        for part in parts:
            part_pp = preprocess(part)
            if part_pp['preproc_type'] == '':
                part_pp['parse_pattern'] = 'compound_part'  # skip LLM routing
                compound_parts.append((r, pp['basis'], part_pp))
                to_search.append((r, part_pp))

    pending = [(r, pp) for r, pp in to_search if pp['parse_pattern'] == 'raw']
    print(f'  excluded : {len(excluded)}  compound : {len(compound_raw)} '
          f'({len(compound_parts)} parts)  '
          f'to search: {len(to_search)}  (llm_pending: {len(pending)})')

    # --- LLM pass: parse llm_pending rows into key + loc ---
    if args.llm and pending:
        llm_ckpt, _ = _llm_ckpt_paths(args.llm_model)
        llm_cache = _load_llm_ckpt(llm_ckpt, args.llm_model)
        ckpt_hits = sum(1 for _, pp in pending if pp['basis'] in llm_cache)
        if ckpt_hits:
            print(f'  LLM checkpoint: resuming ({ckpt_hits}/{len(pending)} already done)')
        print(f'Running LLM on {len(pending) - ckpt_hits} remaining rows...')
        llm_ok = llm_cached = llm_fail = 0
        is_new_ckpt = not os.path.exists(llm_ckpt)
        if is_new_ckpt:
            _write_llm_ckpt_meta(args.llm_model)
        with open(llm_ckpt, 'a', encoding='utf-8', newline='') as ckpt_f:
            ckpt_w = csv.DictWriter(ckpt_f, fieldnames=['basis', 'key', 'loc', 'loc_type'],
                                    delimiter='\t')
            if is_new_ckpt:
                ckpt_w.writeheader()
            with tqdm(pending, unit='row') as bar:
                for r, pp in bar:
                    if pp['basis'] in llm_cache:
                        cached = llm_cache[pp['basis']]
                        pp['key'] = cached['key']
                        pp['loc'] = cached['loc']
                        pp['loc_type'] = cached['loc_type']
                        pp['parse_pattern'] = 'llm'
                        llm_cached += 1
                        llm_ok += 1
                    else:
                        time.sleep(args.llm_delay)
                        result = parse_citation_with_retry(pp['basis'], args.llm_model)
                        if result:
                            pp['key']           = result['key']
                            pp['loc']           = result['loc']
                            pp['loc_type']      = result['loc_type']
                            pp['parse_pattern'] = 'llm'
                            llm_ok += 1
                            ckpt_w.writerow({'basis': pp['basis'], 'key': result['key'],
                                             'loc': result['loc'], 'loc_type': result['loc_type']})
                            ckpt_f.flush()
                        else:
                            llm_fail += 1
                    bar.set_postfix(ok=llm_ok, cached=llm_cached, fail=llm_fail)
        print(f'  LLM parsed: {llm_ok} (from cache: {llm_cached})  failed: {llm_fail}')

    if args.dry_run:
        for r, pp in to_search:
            orig = f"  ← {r.get('basis','')!r}" if pp['parse_pattern'] == 'compound_part' else ''
            print(f"  [{pp['parse_pattern']:14s}] key={pp['key']!r:35s}  "
                  f"loc={pp['loc']!r}  ({r.get('freq', '?')}×){orig}")
        print('(dry-run: no API calls made, no output written)')
        return

    # Pre-populate key_map before dedup: known_qids.tsv is the single source of truth.
    # Vetted sheet keys not yet in the file are promoted into it automatically.
    key_map: dict = dict(_promote_vetted_keys(key_corrections))
    n_file = sum(1 for v in key_map.values() if v[2] == 'known')
    n_vetted = sum(1 for v in key_map.values() if v[2] == 'key_vetted')
    print(f'  known QIDs: {n_file} from {KNOWN_QIDS} + {n_vetted} key_vetted from sheet')

    # --- Deduplicate keys, preserving frequency order ---
    seen_keys: set = set()
    unique_keys = []
    key_to_pattern: dict = {}
    for _, pp in to_search:
        k = pp['key']
        if not k:
            continue   # rows with no key (e.g. empty after preprocess) are skipped
        if k in key_map or k in seen_keys:
            continue
        seen_keys.add(k)
        unique_keys.append(k)
        key_to_pattern[k] = pp['parse_pattern']
    if args.api_limit:
        unique_keys = unique_keys[:args.api_limit]
        print(f'  unique keys: {len(unique_keys)} (limited to top {args.api_limit})  '
              f'(dedup saves {len(to_search) - len(unique_keys)} API calls)')
    else:
        print(f'  unique keys: {len(unique_keys)}  '
              f'(dedup saves {len(to_search) - len(unique_keys)} API calls)')

    # --- API lookup: one call per unique key ---
    api_cache = _load_api_ckpt(API_CKPT)
    api_hits = sum(1 for k in unique_keys if k in api_cache)
    if api_hits:
        print(f'  API checkpoint: resuming ({api_hits}/{len(unique_keys)} already done)')
    matched = 0
    is_new_api_ckpt = not os.path.exists(API_CKPT)
    with open(API_CKPT, 'a', encoding='utf-8', newline='') as api_ckpt_f:
        api_ckpt_w = csv.DictWriter(api_ckpt_f, fieldnames=['key', 'qid', 'label', 'mtype'],
                                    delimiter='\t')
        if is_new_api_ckpt:
            api_ckpt_w.writeheader()
        with tqdm(unique_keys, unit='key') as bar:
            for key in bar:
                if key in api_cache:
                    qid, label, mtype = api_cache[key]
                else:
                    qid, label, _, subtype = api_search_one(key, key_to_pattern.get(key, ''))
                    if qid:
                        mtype = f'api_{subtype}' if subtype in ('label', 'alias') else 'api_fuzzy'
                    else:
                        qid = label = mtype = ''
                    api_ckpt_w.writerow({'key': key, 'qid': qid, 'label': label, 'mtype': mtype})
                    api_ckpt_f.flush()
                if qid:
                    matched += 1
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
    patched = 0
    for r in resolved_rows:
        mtype = r.get('match_type', '')
        qid   = extract_qid(r.get('qid', ''))
        label = r.get('label', '')
        if mtype in ('none', 'excluded', 'shelfmark'):
            key = r.get('key', '').strip()
            hit_qid, hit_label, hit_mtype = key_map.get(key, ('', '', ''))
            if hit_qid:
                qid, label, mtype = hit_qid, hit_label, hit_mtype
                patched += 1
        out_rows.append(out_row(
            r.get('freq', ''), r['basis'],
            r.get('key', ''), r.get('loc', ''), r.get('loc_type', ''),
            mtype, qid, label,
            vetted=vetted_value(mtype) or r.get('vetted', ''),
            parse_pattern=r.get('parse_pattern', ''),
        ))
    if patched:
        print(f'  Patched {patched} none→known from known_qids.tsv')
    for r, pp in excluded:
        out_rows.append(out_row(r.get('freq', ''), pp['basis'], pp['key'],
                                pp['loc'], pp['loc_type'], 'excluded', '', '',
                                parse_pattern=pp['parse_pattern']))
    for r, orig_basis, part_pp in compound_parts:
        qid, label, mtype = key_map.get(part_pp['key'], ('', '', ''))
        if not mtype:
            mtype = 'none'
        out_rows.append(out_row(r.get('freq', ''), orig_basis, part_pp['key'],
                                part_pp['loc'], part_pp['loc_type'], mtype, qid, label,
                                vetted=vetted_value(mtype),
                                parse_pattern=part_pp['parse_pattern']))
    for r, pp in to_search:
        if pp['parse_pattern'] == 'compound_part':
            continue  # already emitted in compound_parts block above
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
    print(f'  vetted         : {mc["vetted"]}')
    print(f'  excluded       : {mc["excluded"]}')
    print(f'  api_label      : {mc["api_label"]}')
    print(f'  api_alias      : {mc["api_alias"]}')
    print(f'  api_fuzzy      : {mc["api_fuzzy"]}')
    print(f'  none           : {mc["none"]}')
    print(f'  llm_pending    : {mc["llm_pending"]}')


if __name__ == '__main__':
    main()
