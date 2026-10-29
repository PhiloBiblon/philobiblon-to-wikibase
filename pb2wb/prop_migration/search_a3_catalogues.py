"""
search_a3_catalogues.py — read-only wbsearchentities lookup for the A3 catalogue prefixes.

Reads a3_catalogue_search_terms.tsv (rows with action=search), searches FactGrid
labels and aliases in es then en (5 hits each), and writes a3_catalogue_candidates.tsv
with up to 5 distinct hits per term. Nothing is written to FactGrid.

Usage (from pb2wb/):
    python prop_migration/search_a3_catalogues.py
"""

import csv
import logging

import requests

import common.factgrid_access  # noqa: F401  (patches requests: UA, throttle, reputation)

API = 'https://database.factgrid.de/w/api.php'
IN_TSV = 'prop_migration/a3_catalogue_search_terms.tsv'
OUT_TSV = 'prop_migration/a3_catalogue_candidates.tsv'
MAX_HITS = 5


def search(session, term, lang):
    resp = session.get(API, params={
        'action': 'wbsearchentities', 'search': term, 'language': lang,
        'uselang': lang, 'type': 'item', 'limit': MAX_HITS, 'format': 'json',
    }, timeout=20)
    resp.raise_for_status()
    return resp.json().get('search', [])


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%H:%M:%S')
    session = requests.Session()
    with open(IN_TSV, encoding='utf-8', newline='') as f:
        rows = [r for r in csv.DictReader(f, delimiter='\t') if r['action'] == 'search']
    with open(OUT_TSV, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t')
        w.writerow(['search_term', 'usages', 'prefixes', 'note', 'rank', 'qid', 'label',
                    'description', 'matched_text', 'lang'])
        for r in rows:
            term = r['search_term_or_qid']
            seen = []
            for lang in ('es', 'en'):
                for h in search(session, term, lang):
                    if h['id'] not in [s[0] for s in seen]:
                        seen.append((h['id'], h.get('label', ''), h.get('description', ''),
                                     h.get('match', {}).get('text', ''), lang))
            logging.info('%-45s %d hits', term, len(seen))
            if not seen:
                w.writerow([term, r['usages'], r['prefixes'], r['note'], '', '', '', '', '', ''])
            for i, s in enumerate(seen[:MAX_HITS], 1):
                w.writerow([term, r['usages'], r['prefixes'], r['note'], i, *s])
    logging.info('wrote %s', OUT_TSV)


if __name__ == '__main__':
    main()
