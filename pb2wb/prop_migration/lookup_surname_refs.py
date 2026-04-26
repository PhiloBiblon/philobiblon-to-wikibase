"""
lookup_surname_refs.py — find FactGrid QIDs for single-surname P721 basis strings.

For each single-surname key with match_type=none, queries FactGrid for items
where the label starts with that surname AND the item has a PhiloBiblon bibid
(P476 containing "bibid"), indicating it's a bibliographic reference work.

Results are written to a candidates TSV for Charles to review.  Once confirmed,
add entries to known_qids.tsv.

Usage (from pb2wb/):
    python prop_migration/lookup_surname_refs.py
    python prop_migration/lookup_surname_refs.py --dry-run
    python prop_migration/lookup_surname_refs.py --out prop_migration/surname_candidates.tsv
"""

import argparse
import csv
import os
import re
import sys
import time

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.dirname(dir_path))

import requests

CANDIDATES  = 'prop_migration/basis_candidates.tsv'
KNOWN_QIDS  = 'prop_migration/known_qids.tsv'
OUT_DEFAULT = 'prop_migration/surname_candidates.tsv'

_SPARQL_URL = 'https://database.factgrid.de/sparql'
_HEADERS    = {'User-Agent': 'pb2wb/1.0', 'Accept': 'application/json'}
_SURNAME_RE = re.compile(r'^[A-ZÁÉÍÓÚ][a-záéíóúü\-]+$')


def load_known_keys(path):
    known = set()
    if not os.path.exists(path):
        return known
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            known.add(row.get('key', '').strip())
    return known


def load_surname_rows(candidates_path, known_keys):
    """Return list of (freq, basis, key) for single-surname none rows not already known."""
    rows = []
    seen_keys = set()
    with open(candidates_path, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            if row.get('match_type') != 'none':
                continue
            key = row.get('key', '').strip()
            if not _SURNAME_RE.match(key):
                continue
            if key in known_keys or key in seen_keys:
                continue
            seen_keys.add(key)
            rows.append((int(row.get('freq', '0') or 0), row.get('basis', ''), key))
    rows.sort(reverse=True)
    return rows


def query_bibid_refs(key, timeout=20):
    """
    Return list of (qid, label) for FG items where:
      - label starts with key (case-insensitive)
      - item has P476 containing "bibid" (PhiloBiblon bibliographic reference)
    """
    sparql = f"""
SELECT DISTINCT ?item ?label WHERE {{
  ?item wdt:P476 ?pbid .
  FILTER(CONTAINS(LCASE(STR(?pbid)), "bibid"))
  ?item rdfs:label ?label .
  FILTER(LANG(?label) = "en")
  FILTER(STRSTARTS(LCASE(?label), "{key.lower()}"))
}} LIMIT 5"""
    try:
        r = requests.get(_SPARQL_URL, params={'query': sparql, 'format': 'json'},
                         headers=_HEADERS, timeout=timeout)
        hits = []
        for b in r.json().get('results', {}).get('bindings', []):
            qid   = b['item']['value'].split('/')[-1]
            label = b['label']['value']
            hits.append((qid, label))
        # Deduplicate (same QID can appear multiple times due to multiple labels)
        seen = set()
        deduped = []
        for qid, label in hits:
            if qid not in seen:
                seen.add(qid)
                deduped.append((qid, label))
        return deduped
    except Exception as e:
        return []


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--candidates', default=CANDIDATES)
    parser.add_argument('--known',      default=KNOWN_QIDS)
    parser.add_argument('--out',        default=OUT_DEFAULT)
    parser.add_argument('--limit',      type=int, default=0,
                        help='Only query the top N surnames (default: all)')
    parser.add_argument('--dry-run',    action='store_true')
    args = parser.parse_args()

    known_keys = load_known_keys(args.known)
    rows = load_surname_rows(args.candidates, known_keys)

    if args.limit:
        rows = rows[:args.limit]

    print(f'Single-surname none rows to query: {len(rows)}')

    results = []   # (freq, key, qid, label, n_hits)
    found = none_ = ambiguous = 0

    from tqdm import tqdm
    with tqdm(rows, unit='name') as bar:
        for freq, basis, key in bar:
            bar.set_postfix(key=key, found=found, ambig=ambiguous)
            hits = query_bibid_refs(key)
            if hits:
                for qid, label in hits:
                    results.append({
                        'key':     key,
                        'freq':    freq,
                        'qid':     qid,
                        'label':   label,
                        'n_hits':  len(hits),
                        'note':    'AMBIGUOUS — review' if len(hits) > 1 else '',
                    })
                if len(hits) == 1:
                    found += 1
                else:
                    ambiguous += 1
            else:
                results.append({'key': key, 'freq': freq, 'qid': '', 'label': '', 'n_hits': 0, 'note': 'not found'})
                none_ += 1
            time.sleep(0.4)

    print(f'  unambiguous match: {found}')
    print(f'  ambiguous (>1 hit): {ambiguous}')
    print(f'  not found: {none_}')

    if args.dry_run:
        for r in results[:20]:
            flag = '*' if r['n_hits'] == 1 else (' ?' if r['n_hits'] > 1 else ' —')
            print(f"  {flag} {r['freq']:>4}  {r['key']:20s}  {r['qid']:10s}  {r['label'][:50]}")
        print('[dry-run] nothing written')
        return

    with open(args.out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['key','freq','qid','label','n_hits','note'],
                           delimiter='\t')
        w.writeheader()
        w.writerows(results)
    print(f'Written: {args.out}  ({len(results)} rows)')


if __name__ == '__main__':
    main()
