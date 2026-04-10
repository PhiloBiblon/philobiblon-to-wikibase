"""
Phase 1: Generate candidate mapping for P1141 (string place) → P241 (item place).

Queries all distinct P1141 values from FactGrid, attempts label matching to
FactGrid items in two passes, and writes a TSV for manual review in Google Sheets.

Matching strategy
-----------------
Pass 1 — bulk exact-label SPARQL (case-insensitive, all languages, one query).
Pass 2 — wbsearchentities API for still-unmatched values (fuzzy, one call each).
  match_type 'exact_label' : high confidence, Charles can likely accept as-is
  match_type 'api_search'  : lower confidence (misspelling/variant), needs vetting
  match_type 'none'        : no candidate found; place may not exist in FactGrid yet

Usage (from pb2wb/):
    python prop_migration/generate_place_mapping.py --out prop_migration/place_mapping.tsv
"""

import os
import sys
import argparse
import csv
import unicodedata

dir_path = os.path.dirname(os.path.realpath(__file__))
parent_dir_path = os.path.dirname(dir_path)
sys.path.append(parent_dir_path)

# Must set TEMP_WB before importing WBManager so it picks up FACTGRID config.
from common.settings import TEMP_DICT, BASE_IMPORT_OBJECTS
TEMP_DICT['TEMP_WB'] = 'FACTGRID'

from common.wb_manager import WBManager
from wikibaseintegrator import wbi_helpers

STRING_PROP = 'P1141'

TSV_COLUMNS = [
    'p1141_value',     # original string value from FactGrid
    'count',           # number of items that carry this value
    'candidate_qid',   # auto-matched QID (may be blank)
    'candidate_label', # label of candidate item (en or first available)
    'match_type',      # 'exact_label', 'api_search', or 'none'
    'approved_qid',    # BLANK — for Charles to fill in
    'notes',           # BLANK — for Charles to add notes
]

# FactGrid SPARQL endpoint and prefix (read directly to avoid re-instantiating WBManager)
FG_SPARQL = BASE_IMPORT_OBJECTS['FACTGRID']['SPARQL_ENDPOINT_URL']
FG_PREFIX  = BASE_IMPORT_OBJECTS['FACTGRID']['SPARQL_PREFIX']
FG_API     = BASE_IMPORT_OBJECTS['FACTGRID']['MEDIAWIKI_API_URL']


def normalize(s):
    """Lowercase + strip diacritics for loose comparison."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', s.lower())
        if unicodedata.category(c) != 'Mn'
    )


def get_distinct_values(wb_manager):
    """Return list of (value, count) sorted by count descending."""
    query = f"""
        SELECT ?value (COUNT(?item) AS ?count) WHERE {{
            ?item wdt:{STRING_PROP} ?value .
        }}
        GROUP BY ?value
        ORDER BY DESC(?count)
    """
    rows = wb_manager.runSparQlQuery(query)
    if not rows:
        return []
    return [(r['value']['value'], int(r['count']['value'])) for r in rows]


def bulk_exact_match(values, prefix):
    """
    One SPARQL query: find FactGrid items whose rdfs:label exactly matches
    any of the given values (case-insensitive, any language).

    Returns dict: normalized(value) → (qid, label)
    """
    # Build VALUES block — escape quotes just in case
    literals = ' '.join(f'"{v.replace(chr(34), chr(92)+chr(34))}"' for v in values)
    query = f"""
        SELECT DISTINCT ?item ?itemLabel WHERE {{
            VALUES ?searchLabel {{ {literals} }}
            ?item rdfs:label ?itemLabel .
            FILTER(LCASE(STR(?itemLabel)) = LCASE(STR(?searchLabel)))
            FILTER CONTAINS(STR(?item), '/Q')
        }}
    """
    results = wbi_helpers.execute_sparql_query(query, prefix)
    matches = {}
    for row in results.get('results', {}).get('bindings', []):
        qid   = row['item']['value'].split('/')[-1]
        label = row['itemLabel']['value']
        key   = normalize(label)
        # Keep first result per normalized label
        if key not in matches:
            matches[key] = (qid, label)
    return matches


def api_search(value, api_url):
    """
    Use wbsearchentities to find the top candidate for a single string.
    Returns (qid, label) or ('', '').
    """
    results = wbi_helpers.search_entities(
        search_string=value,
        language='en',
        search_type='item',
        max_results=1,
        mediawiki_api_url=api_url,
    )
    if results:
        r = results[0]
        return r.get('id', ''), r.get('label', r.get('id', ''))
    return '', ''


def main():
    parser = argparse.ArgumentParser(description='Generate P1141→P241 place mapping TSV')
    parser.add_argument(
        '--out',
        default='prop_migration/place_mapping.tsv',
        help='Output TSV path (default: prop_migration/place_mapping.tsv)',
    )
    parser.add_argument(
        '--no-api-fallback',
        action='store_true',
        help='Skip the api_search pass (faster, fewer matches)',
    )
    args = parser.parse_args()

    print('Connecting to FactGrid...')
    wb_manager = WBManager()

    print(f'Querying distinct {STRING_PROP} values...')
    values = get_distinct_values(wb_manager)
    if not values:
        print('No values found. Exiting.')
        return
    print(f'Found {len(values)} distinct values.')

    # --- Pass 1: bulk exact-label match ---
    print('Pass 1: bulk exact-label SPARQL...')
    all_strings = [v for v, _ in values]
    exact_matches = bulk_exact_match(all_strings, FG_PREFIX)
    pass1_hits = sum(1 for v, _ in values if normalize(v) in exact_matches)
    print(f'  Exact matches: {pass1_hits}/{len(values)}')

    # --- Pass 2: api_search for unmatched ---
    unmatched = [(v, c) for v, c in values if normalize(v) not in exact_matches]
    api_matches = {}
    if unmatched and not args.no_api_fallback:
        print(f'Pass 2: api_search for {len(unmatched)} unmatched values...')
        for i, (value, _) in enumerate(unmatched, 1):
            qid, label = api_search(value, FG_API)
            if qid:
                api_matches[value] = (qid, label)
            if i % 50 == 0 or i == len(unmatched):
                print(f'  {i}/{len(unmatched)} done ({len(api_matches)} matched so far)')

    # --- Assemble output rows ---
    rows = []
    for value, count in values:
        norm = normalize(value)
        if norm in exact_matches:
            qid, label = exact_matches[norm]
            match_type = 'exact_label'
        elif value in api_matches:
            qid, label = api_matches[value]
            match_type = 'api_search'
        else:
            qid, label, match_type = '', '', 'none'

        rows.append({
            'p1141_value':     value,
            'count':           count,
            'candidate_qid':   qid,
            'candidate_label': label,
            'match_type':      match_type,
            'approved_qid':    '',
            'notes':           '',
        })

    # --- Write TSV ---
    out_path = args.out
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=TSV_COLUMNS, delimiter='\t')
        writer.writeheader()
        writer.writerows(rows)

    exact_n    = sum(1 for r in rows if r['match_type'] == 'exact_label')
    api_n      = sum(1 for r in rows if r['match_type'] == 'api_search')
    none_n     = sum(1 for r in rows if r['match_type'] == 'none')
    print(f'\nDone.')
    print(f'  exact_label : {exact_n}')
    print(f'  api_search  : {api_n}  (candidates need vetting)')
    print(f'  none        : {none_n}  (not in FactGrid yet, or unrecognized)')
    print(f'Output: {out_path}')


if __name__ == '__main__':
    main()
