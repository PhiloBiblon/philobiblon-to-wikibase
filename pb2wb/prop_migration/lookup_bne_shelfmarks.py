"""
lookup_bne_shelfmarks.py — find FactGrid QIDs for BNE manuscript shelfmarks
by searching label text via SPARQL (wbsearchentities misses these because the
shelfmark appears mid-label, not at the start).

Reads basis_candidates.tsv, collects all BNE MSS/NNNN keys with match_type=none,
queries FactGrid in batches, and writes matches to known_qids.tsv.

Usage (from pb2wb/):
    python prop_migration/lookup_bne_shelfmarks.py
    python prop_migration/lookup_bne_shelfmarks.py --dry-run
"""

import argparse
import csv
import os
import sys
import time

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.dirname(dir_path))

from common.settings import BASE_IMPORT_OBJECTS
from wikibaseintegrator import wbi_helpers

FG          = BASE_IMPORT_OBJECTS['FACTGRID']
CANDIDATES  = 'prop_migration/basis_candidates.tsv'
KNOWN_QIDS  = 'prop_migration/known_qids.tsv'
BATCH_SIZE  = 5    # shelfmarks per SPARQL query


def load_candidates(path):
    """Return list of (freq, key) for BNE MSS/ keys with match_type=none."""
    rows = []
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            key = row.get('key', '').strip()
            mt  = row.get('match_type', '').strip()
            if key.startswith('BNE MSS/') and mt in ('none', 'shelfmark'):
                rows.append((int(row.get('freq', '0') or 0), key))
    # Deduplicate, keep highest freq
    seen = {}
    for freq, key in rows:
        if key not in seen or freq > seen[key]:
            seen[key] = freq
    return sorted(seen.items(), key=lambda x: -x[1])


def load_known(path):
    """Return set of keys already in known_qids.tsv."""
    known = set()
    if not os.path.exists(path):
        return known
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            known.add(row.get('key', '').strip())
    return known


def query_batch(shelfmarks, prefix):
    """
    Query FactGrid for items whose English label contains any of the shelfmarks.
    Returns dict {shelfmark: [(qid, label), ...]}
    """
    filters = ' || '.join(
        f'CONTAINS(?label, "{s}")'
        for s in shelfmarks
    )
    sparql = f"""
SELECT ?item ?label WHERE {{
  ?item rdfs:label ?label .
  FILTER(LANG(?label) = "en")
  FILTER(STRSTARTS(?label, "MS:"))
  FILTER({filters})
}}
"""
    results = wbi_helpers.execute_sparql_query(sparql, prefix)
    hits = {}
    for binding in results.get('results', {}).get('bindings', []):
        qid   = binding['item']['value'].split('/')[-1]
        label = binding['label']['value']
        # Find which shelfmark matched
        for s in shelfmarks:
            if s in label:
                hits.setdefault(s, []).append((qid, label))
    return hits


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--candidates', default=CANDIDATES)
    parser.add_argument('--out',        default=KNOWN_QIDS)
    parser.add_argument('--dry-run',    action='store_true')
    args = parser.parse_args()

    candidates = load_candidates(args.candidates)
    already_known = load_known(args.out)

    to_query = [(freq, key) for freq, key in candidates if key not in already_known]
    print(f'BNE MSS/ none keys: {len(candidates)}  '
          f'({len(already_known)} already known, {len(to_query)} to query)')

    shelfmarks = [key for _, key in to_query]

    found = {}
    for i in range(0, len(shelfmarks), BATCH_SIZE):
        batch = shelfmarks[i:i + BATCH_SIZE]
        print(f'  Querying batch {i//BATCH_SIZE + 1} ({len(batch)} shelfmarks)...', end=' ', flush=True)
        hits = query_batch(batch, FG['SPARQL_PREFIX'])
        for s, matches in hits.items():
            found[s] = matches
        print(f'{len(hits)} matched')
        if i + BATCH_SIZE < len(shelfmarks):
            time.sleep(1)

    print(f'\nMatched: {len(found)} / {len(shelfmarks)}')

    if not found:
        print('Nothing to add.')
        return

    # Show results
    freq_map = {key: freq for freq, key in to_query}
    for key, matches in sorted(found.items(), key=lambda x: -freq_map.get(x[0], 0)):
        freq = freq_map.get(key, 0)
        print(f'  {freq:>4}  {key}')
        for qid, label in matches:
            print(f'         {qid}  {label[:80]}')

    if args.dry_run:
        print('\n[dry-run] nothing written')
        return

    # Append unambiguous matches (exactly one hit) to known_qids.tsv
    added = 0
    is_new = not os.path.exists(args.out)
    with open(args.out, 'a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['key', 'qid', 'label', 'note'], delimiter='\t')
        if is_new:
            w.writeheader()
        for key, matches in sorted(found.items(), key=lambda x: -freq_map.get(x[0], 0)):
            if len(matches) == 1:
                qid, label = matches[0]
                w.writerow({'key': key, 'qid': qid,
                            'label': label[:120],
                            'note': 'SPARQL label-contains match'})
                added += 1
            else:
                print(f'  AMBIGUOUS ({len(matches)} hits for {key!r}) — skipped, review manually')

    print(f'\nAdded {added} entries to {args.out}')


if __name__ == '__main__':
    main()
