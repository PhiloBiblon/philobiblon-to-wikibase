"""
fill_gaps.py — find P241 candidate QIDs for P1141 strings not yet mapped.

Reads:
  unique_strings.tsv          — distinct P1141 strings with counts (SPARQL output)
  P1141-P241 - P1141-P241.tsv — student's sheet with existing P241 Qid mappings

Writes:
  place_candidates.tsv — all 577 strings, one row each, with best candidate QID

Match types (shown in 'match_type' column):
  sheet              — already in student's mapping; trust these
  exact_label        — bulk SPARQL exact label match (any language, case-insensitive)
  exact_label_stripped — matched after removing trailing qualifier (", WI", "[Mass]", etc.)
  latin_lookup       — known Latin place name; searched for the modern equivalent
  api_search         — wbsearchentities fuzzy match; lower confidence, needs vetting
  compound           — string contains multiple cities; pending Charles's decision
  none               — no match found; place may not exist in FactGrid yet

Usage (from pb2wb/):
    python prop_migration/fill_gaps.py
    python prop_migration/fill_gaps.py --no-api   # skip fuzzy pass, faster
"""

import os
import sys
import re
import csv
import unicodedata
import argparse
from itertools import islice

dir_path = os.path.dirname(os.path.realpath(__file__))
parent_dir_path = os.path.dirname(dir_path)
sys.path.append(parent_dir_path)

from common.settings import BASE_IMPORT_OBJECTS
from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator import wbi_helpers

# Configure FactGrid — read-only SPARQL, no login needed
FG = BASE_IMPORT_OBJECTS['FACTGRID']
wbi_config['SPARQL_ENDPOINT_URL'] = FG['SPARQL_ENDPOINT_URL']
wbi_config['MEDIAWIKI_API_URL']   = FG['MEDIAWIKI_API_URL']
FG_PREFIX = FG['SPARQL_PREFIX']

SHEET_TSV   = 'prop_migration/P1141-P241 - P1141-P241.tsv'
STRINGS_TSV = 'prop_migration/unique_strings.tsv'
OUT_TSV     = 'prop_migration/place_candidates.tsv'

OUT_COLUMNS = [
    'p1141_value',      # original string
    'count',            # usage count across all FactGrid items
    'candidate_qid',    # best matched QID (may be blank)
    'candidate_label',  # label of that item
    'match_type',       # see module docstring
    'matched_on',       # the string we actually searched (differs when stripped/latin)
    'approved_qid',     # BLANK — for review
    'notes',            # BLANK — for review
]

# Indicators that a string names two publication cities.
# Space around separator required to avoid matching compound place names
# like "Donostia-San Sebastiá" or "Louvain-la-Neuve".
COMPOUND_RE = re.compile(
    r'\s[-–/]\s'        # " - ", " – ", " / "
    r'|\s&\s'           # " & "
    r'|\s+and\s+'       # " and "
    r'|;\s'             # "; "
    r'|,\s+and\s'       # ", and "
    r'|\s~\s',          # " ~ "  (seen in "Madrid ~ Frankfurt a M.")
    re.IGNORECASE,
)

# Latin place names → modern name to search FactGrid for.
# Where a Latin name is ambiguous or itself a compound, map to None (→ 'none').
LATIN_LOOKUP = {
    'parisiis':           'Paris',
    'parisis':            'Paris',
    'lutetia':            'Paris',
    'salmanticae':        'Salamanca',
    'venetiis':           'Venice',
    'vindobonae':         'Vienna',
    'vindibonae':         'Vienna',
    'lipsiae':            'Leipzig',
    'matriti':            'Madrid',
    'taurini':            'Turin',
    'olisipone':          'Lisbon',
    'mediolani':          'Milan',
    'coloniae agrippinae':'Cologne',
    'rothomagi':          'Rouen',
    'lugduni':            'Lyon',
    'patavii':            'Padua',
    'florentiae':         'Florence',
    'gottingae':          'Göttingen',
    'bonnae':             'Bonn',
    'panormi':            'Palermo',
    'oeniponte':          'Innsbruck',
    'monasterii':         'Münster',
    'lucae':              'Lucca',
    'pampaelone':         'Pamplona',
    'hafniae':            'Copenhagen',
    'hauniae':            'Copenhagen',
    'taurini / omae':     None,   # compound
    'hamburgi & lipsiae': None,   # compound
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize(s: str) -> str:
    """Lowercase + strip diacritics, for key comparison only."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', s.lower())
        if unicodedata.category(c) != 'Mn'
    )


def is_compound(s: str) -> bool:
    return bool(COMPOUND_RE.search(s))


def stripped_candidates(s: str) -> list[str]:
    """
    For strings like 'Madison, WI' or 'South Hadley [Mass]', generate
    progressively shorter forms to try.  Always returns the original first.
    """
    results = [s]

    # Strip trailing [...] e.g. "South Hadley [Mass]"
    t = re.sub(r'\s*\[.*?\]\s*$', '', s).strip()
    if t and t != s:
        results.append(t)

    # Strip trailing (...) e.g. "Boston (Massachusetts)"
    t = re.sub(r'\s*\(.*?\)\s*$', '', s).strip()
    if t and t != s and t not in results:
        results.append(t)

    if ',' in s:
        # Strip after last comma e.g. "Vitória, Espíritu Santo, Brasil" → "Vitória, Espíritu Santo"
        t = s[:s.rfind(',')].strip()
        if t and t not in results:
            results.append(t)
        # Strip after first comma e.g. "Vitória, Espíritu Santo, Brasil" → "Vitória"
        t = s[:s.index(',')].strip()
        if t and t not in results:
            results.append(t)

    return results


def chunked(iterable, n):
    it = iter(iterable)
    while True:
        chunk = list(islice(it, n))
        if not chunk:
            break
        yield chunk


# ---------------------------------------------------------------------------
# Matching passes
# ---------------------------------------------------------------------------

# Languages to try for each label — covers the main languages of publication
# places in this corpus (Romance, Germanic, Latin, plus a few others).
LABEL_LANGS = ['en', 'es', 'fr', 'de', 'pt', 'it', 'ca', 'la', 'gl', 'nl', 'cy', 'eu',
               'sl', 'hr', 'cs', 'pl', 'ro', 'hu', 'tr', 'ar', 'he', 'ko', 'ja', 'zh']


def build_sparql_query(chunk: list[str]) -> str:
    """
    Build a SELECT query (no PREFIX lines) using language-tagged literals so
    Blazegraph can use its {predicate, value} index instead of a full label scan.
    The PREFIX is added by execute_sparql_query (or printed separately in dry-run).
    """
    literals = []
    for v in chunk:
        escaped = v.replace('\\', '\\\\').replace('"', '\\"')
        for lang in LABEL_LANGS:
            literals.append(f'"{escaped}"@{lang}')
    values_block = '\n        '.join(literals)
    return f"""SELECT DISTINCT ?item (STR(?itemLabel) AS ?label) WHERE {{
    VALUES ?itemLabel {{
        {values_block}
    }}
    ?item rdfs:label ?itemLabel .
    FILTER CONTAINS(STR(?item), '/Q')
}}"""


def bulk_sparql_match(search_strings: list[str], chunk_size: int = 15,
                      dry_run: bool = False) -> dict[str, tuple[str, str]]:
    """
    One SPARQL query per chunk of `chunk_size` strings.
    Returns dict: normalize(label) → (qid, label).
    In dry_run mode, prints queries and returns empty dict.
    """
    # Maps normalize(label) → list of (qid, label) — may be multiple items per label.
    seen: dict[str, list[tuple[str, str]]] = {}
    unique = list(dict.fromkeys(search_strings))  # preserve order, deduplicate
    total_chunks = (len(unique) + chunk_size - 1) // chunk_size
    for i, chunk in enumerate(chunked(unique, chunk_size), 1):
        query = build_sparql_query(chunk)
        if dry_run:
            print(f'\n-- Chunk {i}/{total_chunks} ({len(chunk)} strings) --')
            print(FG_PREFIX.strip())
            print(query)
            print()
            continue
        print(f'  SPARQL chunk {i}/{total_chunks} ({len(chunk)} strings)...')
        try:
            resp = wbi_helpers.execute_sparql_query(query, FG_PREFIX)
            for row in resp.get('results', {}).get('bindings', []):
                qid   = row['item']['value'].split('/')[-1]
                label = row['label']['value']
                key   = normalize(label)
                if key not in seen:
                    seen[key] = []
                if (qid, label) not in seen[key]:
                    seen[key].append((qid, label))
        except Exception as e:
            print(f'    WARNING: chunk failed — {e}')
    # Sort each hit list by QID number ascending: lower QID = older/more canonical item.
    for key in seen:
        seen[key].sort(key=lambda x: int(x[0][1:]))
    return seen


def api_search_one(value: str) -> tuple[str, str]:
    """Return (qid, label) or ('', '') via wbsearchentities."""
    hits = wbi_helpers.search_entities(
        search_string=value,
        language='en',
        search_type='item',
        max_results=1,
        mediawiki_api_url=FG['MEDIAWIKI_API_URL'],
    )
    if hits:
        r = hits[0]
        return r.get('id', ''), r.get('label', '')
    return '', ''


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Generate P1141→P241 candidate mapping')
    parser.add_argument('--sheet',   default=SHEET_TSV,   help='Student sheet TSV')
    parser.add_argument('--strings', default=STRINGS_TSV, help='Distinct P1141 strings TSV')
    parser.add_argument('--out',     default=OUT_TSV,     help='Output TSV path')
    parser.add_argument('--no-api',  action='store_true', help='Skip API search pass')
    parser.add_argument('--dry-run', action='store_true', help='Print SPARQL queries instead of running them')
    args = parser.parse_args()

    # --- Load inputs ---
    sheet = {}
    with open(args.sheet, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            s = row['_Place_of_publication'].strip()
            q = row['P241 Qid'].strip()
            if q and s not in sheet:
                sheet[s] = q

    strings = []
    with open(args.strings, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            s = row['string'].strip()
            if s:
                strings.append((s, int(row['count'])))

    print(f'{len(strings)} distinct strings; {len(sheet)} seeded from student sheet')

    # --- Classify each string ---
    # result_rows accumulates final output; gaps feeds the matching passes.
    result_rows: list[dict] = []
    gaps: list[tuple[str, int, list[str], str]] = []  # (string, count, candidates, prefix_mtype)

    for string, count in strings:
        # Already mapped by student
        if string in sheet:
            result_rows.append(_row(string, count, sheet[string], string, 'sheet', string))
            continue

        norm = normalize(string)

        # Known Latin name
        if norm in LATIN_LOOKUP:
            modern = LATIN_LOOKUP[norm]
            if modern is None:
                result_rows.append(_row(string, count, '', '', 'compound', ''))
            else:
                gaps.append((string, count, [modern], 'latin_lookup'))
            continue

        # Compound string (multiple cities)
        if is_compound(string):
            result_rows.append(_row(string, count, '', '', 'compound', ''))
            continue

        # Normal: try original + stripped variants
        candidates = stripped_candidates(string)
        gaps.append((string, count, candidates, ''))

    print(f'{len(result_rows)} already resolved ({len(sheet)} sheet + compounds/latin-none)')
    print(f'{len(gaps)} strings need matching')

    # --- Pass 1: bulk SPARQL ---
    print('\nPass 1: bulk exact-label SPARQL...')
    all_candidates = [c for _, _, cands, _ in gaps for c in cands]
    sparql_hits = bulk_sparql_match(all_candidates, dry_run=args.dry_run)
    if args.dry_run:
        print('(dry-run: no queries executed, no output file written)')
        return
    print(f'SPARQL returned {len(sparql_hits)} distinct label matches')

    still_unmatched: list[tuple[str, int, list[str], str]] = []
    for string, count, candidates, prefix_mtype in gaps:
        matched = False
        for c in candidates:
            key = normalize(c)
            if key in sparql_hits:
                hits = sparql_hits[key]
                qid, label = hits[0]  # lowest QID = most canonical
                if prefix_mtype == 'latin_lookup':
                    mtype = 'latin_lookup'
                elif c == string:
                    mtype = 'exact_label'
                else:
                    mtype = 'exact_label_stripped'
                notes = f'{len(hits)} items match this label — verify QID' if len(hits) > 1 else ''
                result_rows.append(_row(string, count, qid, label, mtype, c, notes))
                matched = True
                break
        if not matched:
            still_unmatched.append((string, count, candidates, prefix_mtype))

    sparql_matched = len(gaps) - len(still_unmatched)
    print(f'{sparql_matched} matched via SPARQL, {len(still_unmatched)} still unmatched')

    # --- Pass 2: API search ---
    if still_unmatched and not args.no_api:
        print(f'\nPass 2: API search for {len(still_unmatched)} unmatched strings...')
        api_matched = 0
        for i, (string, count, candidates, prefix_mtype) in enumerate(still_unmatched, 1):
            matched = False
            for c in candidates:
                qid, label = api_search_one(c)
                if qid:
                    mtype = 'api_search' if c == string else 'api_search_stripped'
                    result_rows.append(_row(string, count, qid, label, mtype, c))
                    api_matched += 1
                    matched = True
                    break
            if not matched:
                result_rows.append(_row(string, count, '', '', 'none', ''))
            if i % 50 == 0 or i == len(still_unmatched):
                print(f'  {i}/{len(still_unmatched)} done ({api_matched} matched)')
    else:
        for string, count, candidates, _ in still_unmatched:
            result_rows.append(_row(string, count, '', '', 'none', ''))

    # --- Sort by count desc, then string ---
    result_rows.sort(key=lambda r: (-int(r['count']), r['p1141_value']))

    # --- Write output ---
    with open(args.out, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=OUT_COLUMNS, delimiter='\t')
        writer.writeheader()
        writer.writerows(result_rows)

    # --- Summary ---
    from collections import Counter
    mtype_counts = Counter(r['match_type'] for r in result_rows)
    total = len(result_rows)
    print(f'\nOutput: {args.out}  ({total} rows)')
    print(f'  sheet               : {mtype_counts["sheet"]}')
    print(f'  exact_label         : {mtype_counts["exact_label"]}')
    print(f'  exact_label_stripped: {mtype_counts["exact_label_stripped"]}')
    print(f'  latin_lookup        : {mtype_counts["latin_lookup"]}')
    print(f'  api_search          : {mtype_counts["api_search"]}')
    print(f'  api_search_stripped : {mtype_counts["api_search_stripped"]}')
    print(f'  compound            : {mtype_counts["compound"]}')
    print(f'  none                : {mtype_counts["none"]}')


def _row(string, count, qid, label, mtype, matched_on, notes=''):
    return {
        'p1141_value':    string,
        'count':          count,
        'candidate_qid':  qid,
        'candidate_label': label,
        'match_type':     mtype,
        'matched_on':     matched_on,
        'approved_qid':   '',
        'notes':          notes,
    }


if __name__ == '__main__':
    main()
