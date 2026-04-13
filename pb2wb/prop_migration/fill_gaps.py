"""
fill_gaps.py — find P241 candidate QIDs for P1141 strings not yet mapped.

Reads:
  Charles's sheet TSV (default: P1141-P241 - P1141-P241.tsv)
    Column C (_Place_of_publication) — the strings to match; counts derived
      from how many rows share each string.  Charles's hand-corrections to
      column C are automatically picked up here.
    Column F (P241 Qid) — existing mappings used as seeds (skipped in search).

Writes:
  place_candidates.tsv — one row per distinct column-C string, with best
                         candidate QID and match_type for review / merge.

Matching strategy
-----------------
For each unmatched string we generate search candidates (original + stripped
variants) and try them via the wbsearchentities API, which searches both
labels AND aliases.

Candidate generation:
  - bracket content extraction: "City [State]" → also try "State"
  - strip trailing [...]  and  (...)
  - comma stripping: "City, ST" → "City"
  - spaced-hyphen normalisation: "X - Y, ST" → "X-Y, ST" / "X-Y"
    (only when the original has a comma, so real compounds like
     "Madrid - Frankfurt" are left as compound and not searched)

A string is flagged 'compound' only if ALL generated candidates are compound.

CORRECTIONS dict maps normalised input strings to a replacement search term,
for cases the API cannot resolve on its own (e.g. "Washington D. C" →
"Washington, DC").

Compound handling (--llm flag)
-------------------------------
With --llm, compound strings are sent to a local Ollama instance which splits
them into constituent place names.  Each part is then searched normally and the
resolved QIDs are stored as a JSON array in the 'parts' column of
place_candidates.tsv.  merge_candidates.py reads this and emits one sheet row
per part so every city gets its own clickable P241 Qid.

VERIFY verification (--llm-verify flag)
-----------------------------------------
With --llm-verify, all VERIFY-flagged matches (stripped qualifiers, fuzzy hits)
are sent to Ollama together with the item's description to check whether the
match is geographically correct.  Wrong matches (e.g. "Lewisburg, PA" matched
to a West Virginia city) are downgraded to match_type 'rejected' with blank QID,
so they appear as 'no match found' in the sheet rather than misleading Charles.

match_type values
-----------------
  sheet            — already in student's mapping; trust these
  latin_lookup     — known Latin place name; searched for the modern equivalent
  corrections      — matched after applying CORRECTIONS dict (needs vetting)
  api_label        — API matched on the item's primary label (exact)
  api_alias        — API matched on an alias (exact, e.g. Zagreb)
  api_fuzzy        — API returned a hit but text differs from query
  rejected         — LLM verification found the match geographically wrong
  compound         — string contains multiple cities; parts column has resolved QIDs
  none             — no match found; place may not exist in FactGrid yet

For stripped/normalised matches the match_type gains a '_stripped' suffix
and 'matched_on' shows the string actually searched.

Usage (from pb2wb/):
    python prop_migration/fill_gaps.py
    python prop_migration/fill_gaps.py --sheet prop_migration/sheet_updated.tsv
    python prop_migration/fill_gaps.py --llm                  # compound splitting
    python prop_migration/fill_gaps.py --llm-verify           # verify VERIFY rows
    python prop_migration/fill_gaps.py --llm --llm-verify     # both
    python prop_migration/fill_gaps.py --llm-model mistral
    python prop_migration/fill_gaps.py --dry-run
"""

import os
import sys
import re
import csv
import json
import unicodedata
import argparse
import urllib.request

dir_path = os.path.dirname(os.path.realpath(__file__))
parent_dir_path = os.path.dirname(dir_path)
sys.path.append(parent_dir_path)

import requests
from tqdm import tqdm
from common.settings import BASE_IMPORT_OBJECTS

FG = BASE_IMPORT_OBJECTS['FACTGRID']

SHEET_TSV = 'prop_migration/P1141-P241 - P1141-P241.tsv'
OUT_TSV   = 'prop_migration/place_candidates.tsv'

OUT_COLUMNS = [
    'p1141_value',            # column C string (possibly Charles-corrected)
    'count',                  # number of sheet rows sharing this string
    'candidate_qid',          # best matched QID (may be blank)
    'candidate_label',        # primary label of that item
    'candidate_description',  # item description (used for LLM verification)
    'match_type',             # see module docstring
    'matched_on',             # string actually searched (differs when stripped/latin)
    'approved_qid',           # BLANK — for review
    'parts',                  # JSON array of compound parts [{part, qid, label}, ...]
]

COMPOUND_RE = re.compile(
    r'\s[-–/]\s'        # " - ", " – ", " / "
    r'|\s&\s'           # " & "
    r'|\s+and\s+'       # " and "
    r'|;\s'             # "; "
    r'|,\s+and\s'       # ", and "
    r'|\s~\s',          # " ~ "  (seen in "Madrid ~ Frankfurt a M.")
    re.IGNORECASE,
)

SPACED_HYPHEN_RE = re.compile(r'\s+-\s+')

LATIN_LOOKUP = {
    'parisiis':            'Paris',
    'parisis':             'Paris',
    'lutetia':             'Paris',
    'salmanticae':         'Salamanca',
    'venetiis':            'Venice',
    'vindobonae':          'Vienna',
    'vindibonae':          'Vienna',
    'lipsiae':             'Leipzig',
    'matriti':             'Madrid',
    'taurini':             'Turin',
    'olisipone':           'Lisbon',
    'mediolani':           'Milan',
    'coloniae agrippinae': 'Cologne',
    'rothomagi':           'Rouen',
    'lugduni':             'Lyon',
    'patavii':             'Padua',
    'florentiae':          'Florence',
    'gottingae':           'Göttingen',
    'bonnae':              'Bonn',
    'panormi':             'Palermo',
    'oeniponte':           'Innsbruck',
    'monasterii':          'Münster',
    'lucae':               'Lucca',
    'pampaelone':          'Pamplona',
    'hafniae':             'Copenhagen',
    'hauniae':             'Copenhagen',
    'taurini / omae':      None,   # compound
    'hamburgi & lipsiae':  None,   # compound
}

# Normalised key → replacement search string.
# For strings the API cannot resolve on its own.
CORRECTIONS = {
    'washington d. c':  'Washington, DC',
    'washington d. c.': 'Washington, DC',
    'filadélfia':       'Philadelphia',
    'filadelfia':       'Philadelphia',
}

# Only fuzzy matches (where matched text genuinely differs from query) go to
# LLM verification.  Stripped label/alias matches are reliable enough on their
# own — Charles sees "VERIFY" in the sheet and checks the label anyway.
VERIFY_TYPES = {'api_fuzzy', 'api_fuzzy_stripped'}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize(s):
    """Lowercase + strip diacritics, for comparison only."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', s.lower())
        if unicodedata.category(c) != 'Mn'
    )


def extract_qid(cell_value):
    """Extract bare QID from plain text, HYPERLINK formula, or URL."""
    m = re.search(r'Q\d+', cell_value)
    return m.group(0) if m else ''


def is_compound(s):
    return bool(COMPOUND_RE.search(s))


def is_multi_city_compound(s):
    """
    True when a compound string has qualifiers on BOTH sides of the separator,
    indicating two separate city entries rather than a single hyphenated name.
    Qualifiers may be comma-delimited ("City, ST") or parenthetical ("City (ST)").

    "Farnham, Surrey - Burlington, Vermont"         → True
    "Aldershot (Hampshire) - Brookfield (Vermont)"  → True
    "Winston - Salem, N.C."                         → False (qualifier only on right)
    "Genève - Paris"                                → False (no qualifiers)
    """
    m = COMPOUND_RE.search(s)
    if not m:
        return False
    before = s[:m.start()]
    after  = s[m.end():]
    def has_qualifier(part):
        return ',' in part or ('(' in part and ')' in part)
    return has_qualifier(before) and has_qualifier(after)


def stripped_candidates(s):
    """
    Return [original, variant1, ...] with progressively shorter/cleaner forms:
      - bracket content: "City [State]" → also try "State"
      - strip trailing [...]
      - paren content: "City (State)" → also try "State"
      - strip trailing (...)
      - comma stripping: "City, ST" → "City"
      - spaced-hyphen normalisation: "X - Y" → "X-Y"
        (only when original has a comma, to preserve detection of real
         multi-city compounds like "Madrid - Frankfurt" that have no qualifier)
    """
    results = [s]

    # Extract content inside trailing [...]
    m = re.search(r'\[([^\]]+)\]\s*$', s)
    if m:
        t = m.group(1).strip()
        if t and t not in results:
            results.append(t)

    # Strip trailing [...]
    t = re.sub(r'\s*\[.*?\]\s*$', '', s).strip()
    if t and t != s and t not in results:
        results.append(t)

    # Extract content inside trailing (...)
    m = re.search(r'\(([^)]+)\)\s*$', s)
    if m:
        t = m.group(1).strip()
        if t and t not in results:
            results.append(t)

    # Strip trailing (...)
    t = re.sub(r'\s*\(.*?\)\s*$', '', s).strip()
    if t and t != s and t not in results:
        results.append(t)

    # Comma stripping
    if ',' in s:
        t = s[:s.rfind(',')].strip()
        if t and t not in results:
            results.append(t)
        t = s[:s.index(',')].strip()
        if t and t not in results:
            results.append(t)

    # Spaced-hyphen normalisation — only when original has a comma.
    # This rescues "Winston - Salem, N.C." → "Winston-Salem" while leaving
    # true multi-city strings like "Madrid - Frankfurt" as compound.
    if ',' in s:
        extras = []
        for candidate in list(results):
            if SPACED_HYPHEN_RE.search(candidate):
                normalized = SPACED_HYPHEN_RE.sub('-', candidate)
                if normalized not in results and normalized not in extras:
                    extras.append(normalized)
        results.extend(extras)

    return results


# ---------------------------------------------------------------------------
# Sheet loader
# ---------------------------------------------------------------------------

def load_sheet(path):
    """
    Read the sheet and return:
      strings — list of (string, count) sorted by count descending,
                where string is the column C value (possibly hand-corrected)
      seeded  — dict of string → QID for rows where P241 Qid is already filled
    """
    counts = {}
    seeded = {}
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            s = row['_Place_of_publication'].strip()
            if not s:
                continue
            counts[s] = counts.get(s, 0) + 1
            q = extract_qid(row.get('P241 Qid', ''))
            if q and s not in seeded:
                seeded[s] = q
    strings = sorted(counts.items(), key=lambda x: -x[1])
    return strings, seeded


# ---------------------------------------------------------------------------
# API search
# ---------------------------------------------------------------------------

_SESSION = requests.Session()
_SESSION.headers.update({'User-Agent': 'pb2wb-fill-gaps/1.0'})

_RETRY_ADAPTER = requests.adapters.HTTPAdapter(
    max_retries=requests.packages.urllib3.util.retry.Retry(
        total=4,
        backoff_factor=2,          # waits 2, 4, 8, 16 s between retries
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=['GET'],
    )
)
_SESSION.mount('https://', _RETRY_ADAPTER)
_SESSION.mount('http://',  _RETRY_ADAPTER)


def api_search_one(value):
    """
    Search FactGrid via wbsearchentities.
    Returns (qid, label, description, subtype) where subtype is:
      'label'  — matched on primary label, text == value (exact)
      'alias'  — matched on an alias, text == value (exact)
      'fuzzy'  — API returned a hit but matched text differs from query
      ''       — no result
    """
    resp = _SESSION.get(FG['MEDIAWIKI_API_URL'], params={
        'action': 'wbsearchentities',
        'search': value,
        'language': 'en',
        'type': 'item',
        'limit': 1,
        'format': 'json',
    }, timeout=10)
    resp.raise_for_status()
    results = resp.json().get('search', [])
    if not results:
        return '', '', '', ''
    r = results[0]
    qid         = r.get('id', '')
    label       = r.get('label', '')
    description = r.get('description', '')
    match_info  = r.get('match', {})
    match_type  = match_info.get('type', '')
    match_text  = match_info.get('text', '')
    if match_type in ('label', 'alias') and normalize(match_text) == normalize(value):
        return qid, label, description, match_type
    elif qid:
        return qid, label, description, 'fuzzy'
    return '', '', '', ''


# ---------------------------------------------------------------------------
# LLM (Ollama)
# ---------------------------------------------------------------------------

def make_ollama_llm_fn(model='llama3.2'):
    """Returns a callable that sends a prompt to a local Ollama instance."""
    def call(prompt, system_instruction):
        payload = json.dumps({
            'model': model,
            'messages': [
                {'role': 'system', 'content': system_instruction},
                {'role': 'user',   'content': prompt},
            ],
            'stream': False,
            'format': 'json',
        }).encode()
        req = urllib.request.Request(
            'http://localhost:11434/api/chat',
            data=payload,
            headers={'Content-Type': 'application/json'},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            return data['message']['content']
    return call


# --- Compound splitting ---

_SPLIT_SYSTEM = (
    'You are a place name parser. '
    'Given a string that contains multiple place names joined by separators '
    'such as " - ", " – ", " / ", " & ", " and ", ";", " ~ ", etc., '
    'return a JSON object with a single key "places" whose value is an array '
    'of the individual place name strings, cleaned up but kept recognisable. '
    'If you cannot identify multiple distinct places, return {"places": []}. '
    'Examples:\n'
    '  "Genève - Paris"  →  {"places": ["Genève", "Paris"]}\n'
    '  "Farnham, Surrey - Burlington, Vermont"  →  '
    '{"places": ["Farnham, Surrey", "Burlington, Vermont"]}\n'
    '  "Berlin - Boston"  →  {"places": ["Berlin", "Boston"]}\n'
)


def split_compound(s, llm_fn):
    """Ask the LLM to split a compound place string. Returns list of strings."""
    try:
        raw = llm_fn(s, _SPLIT_SYSTEM)
        data = json.loads(raw)
        parts = data.get('places', [])
        return [p.strip() for p in parts if p.strip()]
    except Exception as exc:
        print(f'  LLM split error for {s!r}: {exc}')
        return []


def part_candidates(s):
    """
    Search candidates for one part of a compound place string.
    Unlike stripped_candidates(), qualifier content is NOT extracted as a
    standalone search term — only stripped.  Searching "Hampshire" from
    "Aldershot (Hampshire)" would match the wrong entity entirely.

    Candidates in order:
      1. full string
      2. stripped bracket / paren qualifier
      3. for comma form "City, State": also try "City (State)" before bare "City"
         so FactGrid aliases like "Burlington (Vermont)" are found before
         falling back to bare "Burlington" which may match the wrong city.
      4. bare city name (comma-stripped)
    """
    results = [s]
    # Strip trailing [...]
    t = re.sub(r'\s*\[.*?\]\s*$', '', s).strip()
    if t and t != s and t not in results:
        results.append(t)
    # Strip trailing (...)
    t = re.sub(r'\s*\(.*?\)\s*$', '', s).strip()
    if t and t != s and t not in results:
        results.append(t)
    # Comma form: "Burlington, Vermont" → try "Burlington (Vermont)" then "Burlington"
    if ',' in s:
        city  = s[:s.index(',')].strip()
        state = s[s.index(',') + 1:].strip()
        if state:
            paren_form = f'{city} ({state})'
            if paren_form not in results:
                results.append(paren_form)
        if city and city not in results:
            results.append(city)
    return results


def resolve_parts(parts):
    """
    Search each compound part individually.
    Returns list of dicts: {part, qid, label}.
    Only accepts clean label/alias matches — fuzzy hits are too unreliable
    for the small FactGrid corpus and produce wrong cross-part collisions.
    """
    resolved = []
    for part in parts:
        candidates = part_candidates(part)
        searchable = [c for c in candidates if not is_compound(c)]
        found = {'part': part, 'qid': '', 'label': ''}
        for c in searchable:
            qid, label, _, subtype = api_search_one(c)
            if qid and subtype in ('label', 'alias'):
                found['qid']   = qid
                found['label'] = label
                break
        resolved.append(found)
    return resolved


# --- VERIFY validation ---

_VERIFY_SYSTEM = (
    'You are verifying geographic matches for a bibliography database. '
    'Given an original place name string from a historical publication record '
    'and a candidate item from a knowledge base (with its label and description), '
    'determine whether they refer to the same place. '
    'Pay close attention to state/country qualifiers in the original string. '
    'Return JSON: {"correct": true, "reason": "..."} or {"correct": false, "reason": "..."}. '
    'Examples:\n'
    '  original="Lewisburg, PA"  candidate="Lewisburg / city in West Virginia"  '
    '→ {"correct": false, "reason": "PA is Pennsylvania, not West Virginia"}\n'
    '  original="Durham, NC"  candidate="Durham / city in County Durham, England"  '
    '→ {"correct": false, "reason": "NC is North Carolina, not England"}\n'
    '  original="Madison"  candidate="Madison / city in Wisconsin, United States"  '
    '→ {"correct": true, "reason": "Madison, WI is the most prominent Madison"}\n'
)


def verify_match(original, label, description, llm_fn):
    """
    Ask the LLM whether label/description is the right match for original.
    Returns True (keep) or False (reject).  Defaults to True on any error.
    """
    prompt = (
        f'Original place string: "{original}"\n'
        f'Candidate: "{label}" / {description or "(no description)"}'
    )
    try:
        raw = llm_fn(prompt, _VERIFY_SYSTEM)
        data = json.loads(raw)
        return bool(data.get('correct', True))
    except Exception as exc:
        print(f'  LLM verify error for {original!r}: {exc}')
        return True   # keep on error


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Generate P1141→P241 candidate mapping')
    parser.add_argument('--sheet',      default=SHEET_TSV,  help='Sheet TSV')
    parser.add_argument('--out',        default=OUT_TSV,    help='Output TSV path')
    parser.add_argument('--llm',        action='store_true',
                        help='Use local Ollama to split compound place strings')
    parser.add_argument('--llm-verify', action='store_true',
                        help='Use local Ollama to verify VERIFY-flagged matches')
    parser.add_argument('--llm-model',  default='llama3.2',
                        help='Ollama model name (default: llama3.2)')
    parser.add_argument('--limit',      type=int, default=0,
                        help='Process only the top N strings (for quick integration tests)')
    parser.add_argument('--dry-run',    action='store_true',
                        help='Print what would be searched without calling the API')
    args = parser.parse_args()

    llm_fn = make_ollama_llm_fn(args.llm_model) if (args.llm or args.llm_verify) else None

    strings, seeded = load_sheet(args.sheet)
    if args.limit:
        strings = strings[:args.limit]
    print(f'{len(strings)} distinct strings from sheet; {len(seeded)} already mapped')

    # --- Classify ---
    result_rows = []
    to_search   = []
    compounds   = []   # (string, count) — for LLM splitting

    for string, count in strings:
        if string in seeded:
            result_rows.append(_row(string, count, seeded[string], '', 'sheet', string))
            continue

        norm = normalize(string)

        if norm in CORRECTIONS:
            to_search.append((string, count, [CORRECTIONS[norm]], 'corrections'))
            continue

        if norm in LATIN_LOOKUP:
            modern = LATIN_LOOKUP[norm]
            if modern is None:
                result_rows.append(_row(string, count, '', '', 'compound', ''))
            else:
                to_search.append((string, count, [modern], 'latin_lookup'))
            continue

        # Multi-city compounds ("City1, ST - City2, ST") go straight to LLM;
        # don't try to generate API candidates for them.
        if is_multi_city_compound(string):
            if args.llm:
                compounds.append((string, count))
            else:
                result_rows.append(_row(string, count, '', '', 'compound', ''))
            continue

        candidates = stripped_candidates(string)
        searchable = [c for c in candidates if not is_compound(c)]

        if not searchable:
            # Compound with no non-compound candidates (e.g. "Genève - Paris")
            if args.llm:
                compounds.append((string, count))
            else:
                result_rows.append(_row(string, count, '', '', 'compound', ''))
            continue

        # Strings that are compound but have non-compound stripped/normalized
        # candidates (e.g. "Winston - Salem, N.C." → "Winston-Salem") are
        # searched via API; only a clean label/alias hit is accepted, fuzzy
        # falls back to LLM compound split.
        original_compound = is_compound(string)
        to_search.append((string, count, searchable, '', original_compound))

    print(f'{len(result_rows)} pre-resolved  '
          f'({len(seeded)} sheet + compounds + latin-none)')
    print(f'{len(to_search)} strings to search via API')
    if compounds:
        print(f'{len(compounds)} compounds queued for LLM splitting')

    if args.dry_run:
        for string, count, candidates, prefix_mtype, *_ in to_search:
            tag = f'[{prefix_mtype}] ' if prefix_mtype else ''
            print(f'  {tag}{candidates}')
        if compounds:
            print('  [compounds]', [s for s, _ in compounds])
        print('(dry-run: no API calls made, no output written)')
        return

    # --- API pass ---
    matched = 0
    with tqdm(to_search, unit='place') as bar:
        for string, count, candidates, prefix_mtype, *rest in bar:
            original_compound = rest[0] if rest else False
            found = False
            for c in candidates:
                qid, label, desc, subtype = api_search_one(c)
                if qid:
                    stripped = (c != string)
                    if prefix_mtype in ('latin_lookup', 'corrections'):
                        mtype = prefix_mtype
                        clean  = True
                    elif subtype in ('label', 'alias'):
                        mtype = f'api_{subtype}' + ('_stripped' if stripped else '')
                        clean  = True
                    else:
                        mtype = 'api_fuzzy' + ('_stripped' if stripped else '')
                        clean  = False
                    # For originally-compound strings, only accept a clean hit;
                    # fuzzy means the normalized form didn't really match — fall
                    # back to LLM compound splitting.
                    if original_compound and not clean:
                        break
                    result_rows.append(_row(string, count, qid, desc, mtype, c,
                                           label=label))
                    matched += 1
                    found = True
                    break
            if not found:
                if original_compound and args.llm:
                    compounds.append((string, count))
                else:
                    result_rows.append(_row(string, count, '', '', 'none', ''))
            bar.set_postfix(matched=matched)

    # --- LLM VERIFY pass ---
    if args.llm_verify:
        verify_rows = [r for r in result_rows if r['match_type'] in VERIFY_TYPES]
        print(f'LLM verification for {len(verify_rows)} VERIFY-flagged matches...')
        rejected = 0
        retry_strings = []   # (original_string, count) for rejected rows
        with tqdm(verify_rows, unit='row') as bar:
            for r in bar:
                ok = verify_match(r['p1141_value'], r['candidate_label'],
                                  r['candidate_description'], llm_fn)
                if not ok:
                    r['match_type']             = 'rejected'
                    r['candidate_qid']          = ''
                    r['candidate_label']        = ''
                    r['candidate_description']  = ''
                    retry_strings.append((r['p1141_value'], r['count']))
                    rejected += 1
                bar.set_postfix(rejected=rejected)
        print(f'  {rejected} matches rejected')

        # Retry rejected rows: search the original string directly (un-stripped).
        # "Durham, NC" was rejected because "Durham" matched Durham UK; searching
        # "Durham, NC" verbatim may find the correct FactGrid item via alias.
        if retry_strings:
            print(f'  Retrying {len(retry_strings)} rejected strings verbatim...')
            retry_map = {s: r for r in result_rows
                         for s in [r['p1141_value']] if r['match_type'] == 'rejected'}
            rescued = 0
            for original, count in retry_strings:
                qid, label, desc, subtype = api_search_one(original)
                if qid and subtype in ('label', 'alias'):
                    r = retry_map[original]
                    r['match_type']            = f'api_{subtype}_retry'
                    r['candidate_qid']         = qid
                    r['candidate_label']       = label
                    r['candidate_description'] = desc
                    r['matched_on']            = original
                    rescued += 1
            print(f'  {rescued} rescued by verbatim retry')

    # --- LLM compound splitting ---
    if compounds:
        print(f'LLM splitting {len(compounds)} compound strings...')
        llm_resolved = 0
        with tqdm(compounds, unit='compound') as bar:
            for string, count in bar:
                parts_list = split_compound(string, llm_fn)
                if parts_list:
                    resolved = resolve_parts(parts_list)
                    parts_json = json.dumps(resolved, ensure_ascii=False)
                    llm_resolved += 1
                else:
                    parts_json = ''
                result_rows.append(_row(string, count, '', '', 'compound', '',
                                        parts=parts_json))
                bar.set_postfix(resolved=llm_resolved)

    result_rows.sort(key=lambda r: (-int(r['count']), r['p1141_value']))

    with open(args.out, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=OUT_COLUMNS, delimiter='\t')
        writer.writeheader()
        writer.writerows(result_rows)

    from collections import Counter
    mc = Counter(r['match_type'] for r in result_rows)
    print(f'\nOutput: {args.out}  ({len(result_rows)} rows)')
    print(f'  sheet              : {mc["sheet"]}')
    print(f'  latin_lookup       : {mc["latin_lookup"]}')
    print(f'  corrections        : {mc["corrections"]}')
    print(f'  api_label          : {mc["api_label"]}')
    print(f'  api_label_stripped : {mc["api_label_stripped"]}')
    print(f'  api_alias          : {mc["api_alias"]}')
    print(f'  api_alias_stripped : {mc["api_alias_stripped"]}')
    print(f'  api_fuzzy          : {mc["api_fuzzy"]}')
    print(f'  api_fuzzy_stripped : {mc["api_fuzzy_stripped"]}')
    print(f'  api_label_retry    : {mc["api_label_retry"]}')
    print(f'  api_alias_retry    : {mc["api_alias_retry"]}')
    print(f'  rejected           : {mc["rejected"]}')
    print(f'  compound           : {mc["compound"]}')
    print(f'  none               : {mc["none"]}')


def _row(string, count, qid, description, mtype, matched_on,
         label='', parts=''):
    return {
        'p1141_value':           string,
        'count':                 count,
        'candidate_qid':         qid,
        'candidate_label':       label,
        'candidate_description': description,
        'match_type':            mtype,
        'matched_on':            matched_on,
        'approved_qid':          '',
        'parts':                 parts,
    }


if __name__ == '__main__':
    main()
