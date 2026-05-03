"""
lookup_bne_shelfmarks.py — find FactGrid QIDs for BNE manuscript shelfmarks
by searching label text via SPARQL (wbsearchentities misses these because the
shelfmark appears mid-label, not at the start).

Reads basis_candidates.tsv, collects all BNE MSS/NNNN keys with match_type=none,
queries FactGrid in batches, and writes matches to bne_shelfmark_candidates.tsv for review
before manually copying confirmed entries to known_qids.tsv.

NOTE: The current approach (CONTAINS/REGEX on rdfs:label of P476 items) is
unreliable — it finds FG items that merely *mention* the shelfmark in their
label (microfilm records, MANID records, researcher notes, articles) rather
than the canonical manuscript item itself. All results were discarded after
spot-checking (2026-04-27).

Needs a better strategy before use, e.g.:
  - Query for items where a shelfmark property directly equals the BNE call number
  - Filter by item type (manuscript) rather than label contents
  - Use the BNE OPAC API or wbsearchentities with the full "MS: Madrid: Nacional
    (BNE), MSS/NNNN" label form

Usage (from pb2wb/):
    python prop_migration/lookup_bne_shelfmarks.py
    python prop_migration/lookup_bne_shelfmarks.py --dry-run
"""

import argparse
import csv
import os
import re
import sys
import time

import requests

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.dirname(dir_path))

from common.settings import BASE_IMPORT_OBJECTS

FG          = BASE_IMPORT_OBJECTS['FACTGRID']
_HEADERS    = {'User-Agent': 'pb2wb/1.0', 'Accept': 'application/json'}
CANDIDATES  = 'prop_migration/basis_candidates.tsv'
KNOWN_QIDS  = 'prop_migration/bne_shelfmark_candidates.tsv'
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
    return sorted(((freq, key) for key, freq in seen.items()), key=lambda x: -x[0])


def load_known(path):
    """Return set of keys already in known_qids.tsv."""
    known = set()
    if not os.path.exists(path):
        return known
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            known.add(row.get('key', '').strip())
    return known


def query_batch(shelfmarks, retries=4, backoff=5):
    """
    Query FactGrid for manuscript items whose Spanish label starts with the
    canonical BNE label prefix "MS: Madrid: Nacional (BNE), MSS/NNNN".
    Using STRSTARTS avoids ambiguity — it selects the manuscript record itself,
    not works contained within it that merely reference the shelfmark.
    Returns dict {shelfmark: [(qid, label), ...]}. Retries on transient errors.
    """
    filters = ' || '.join(
        f'STRSTARTS(?label, "MS: Madrid: Nacional (BNE), {re.sub(r"^BNE ", "", s)}")'
        for s in shelfmarks
    )
    sparql = f"""
SELECT ?item ?label WHERE {{
  ?item wdt:P476 ?bibid .
  ?item rdfs:label ?label .
  FILTER(LANG(?label) = "es")
  FILTER({filters})
}}
"""
    for attempt in range(retries):
        try:
            resp = requests.get(
                FG['SPARQL_ENDPOINT_URL'],
                params={'query': sparql, 'format': 'json'},
                headers=_HEADERS,
                timeout=30,
            )
            resp.raise_for_status()
            hits = {}
            for binding in resp.json().get('results', {}).get('bindings', []):
                qid   = binding['item']['value'].split('/')[-1]
                label = str(binding['label']['value'])
                for s in shelfmarks:
                    prefix = f'MS: Madrid: Nacional (BNE), {re.sub(r"^BNE ", "", s)}'
                    if label.startswith(prefix):
                        hits.setdefault(s, []).append((qid, label))
            return hits
        except Exception as e:
            if attempt < retries - 1:
                wait = backoff * (2 ** attempt)
                print(f'retrying in {wait}s ({e})...', end=' ', flush=True)
                time.sleep(wait)
            else:
                print(f'failed after {retries} attempts: {e}')
                return {}
    return {}


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

    freq_map = {key: freq for freq, key in to_query}
    found = {}
    added = ambiguous = 0

    out_f = None if args.dry_run else open(args.out, 'a', newline='', encoding='utf-8')
    out_w = None
    if out_f:
        out_w = csv.DictWriter(out_f, fieldnames=['key', 'qid', 'label', 'note'], delimiter='\t')
        if not os.path.exists(args.out) or os.path.getsize(args.out) == 0:
            out_w.writeheader()

    try:
        for i in range(0, len(shelfmarks), BATCH_SIZE):
            batch = shelfmarks[i:i + BATCH_SIZE]
            n_batches = (len(shelfmarks) - 1) // BATCH_SIZE + 1
            print(f'  Querying batch {i//BATCH_SIZE + 1}/{n_batches}'
                  f' ({len(batch)} shelfmarks)...', end=' ', flush=True)
            hits = query_batch(batch)
            print(f'{len(hits)} matched')
            for s, matches in hits.items():
                found[s] = matches
                freq = freq_map.get(s, 0)
                if len(matches) == 1:
                    qid, label = matches[0]
                    print(f'    {freq:>4}  {s}  →  {qid}  {label[:60]}')
                    if not args.dry_run and out_w:
                        out_w.writerow({'key': s, 'qid': qid,
                                        'label': label[:120],
                                        'note': 'SPARQL label-contains match'})
                        out_f.flush()
                    added += 1
                else:
                    print(f'    {freq:>4}  {s}  AMBIGUOUS ({len(matches)} hits) — skipped')
                    ambiguous += 1
            if i + BATCH_SIZE < len(shelfmarks):
                time.sleep(1)
    finally:
        if out_f:
            out_f.close()

    suffix = '[dry-run] ' if args.dry_run else ''
    print(f'\n{suffix}Matched: {len(found)}  unambiguous: {added}  ambiguous: {ambiguous}')


if __name__ == '__main__':
    main()
