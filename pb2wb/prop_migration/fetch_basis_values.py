"""
fetch_basis_values.py — query FactGrid for all distinct P721 qualifier values.

Run this once (or whenever you want a fresh pull) and keep the output TSV
around.  generate_basis_seed.py reads from it instead of hitting FactGrid
directly, so you can re-run the seed pipeline without waiting for SPARQL.

Usage (from pb2wb/):
    python prop_migration/fetch_basis_values.py
    python prop_migration/fetch_basis_values.py --limit 500
    python prop_migration/fetch_basis_values.py --out prop_migration/P721-raw-values.tsv
"""

import os
import sys
import csv
import argparse

dir_path = os.path.dirname(os.path.realpath(__file__))
parent_dir_path = os.path.dirname(dir_path)
sys.path.append(parent_dir_path)

import requests

from common.settings import BASE_IMPORT_OBJECTS

_SESSION = requests.Session()
_SESSION.headers.update({'User-Agent': 'pb2wb-fetch-basis/1.0'})

FG = BASE_IMPORT_OBJECTS['FACTGRID']

OUT_TSV = 'prop_migration/P721-raw-values.tsv'


def build_query(limit=None):
    q = (
        "PREFIX pq: <https://database.factgrid.de/prop/qualifier/>\n"
        "SELECT ?value (COUNT(?stmt) AS ?freq) WHERE {\n"
        "    ?item ?prop ?stmt .\n"
        "    ?stmt pq:P721 ?value .\n"
        "}\n"
        "GROUP BY ?value\n"
        "ORDER BY DESC(?freq)"
    )
    if limit:
        q += f"\nLIMIT {limit}"
    return q


def fetch(limit=None):
    query = build_query(limit)
    resp = _SESSION.get(
        FG['SPARQL_ENDPOINT_URL'],
        params={'query': query, 'format': 'json'},
        headers={'Accept': 'application/sparql-results+json'},
        timeout=300,
    )
    resp.raise_for_status()
    bindings = resp.json()['results']['bindings']
    return [(b['value']['value'], int(b['freq']['value'])) for b in bindings]


def main():
    parser = argparse.ArgumentParser(
        description='Fetch all distinct P721 values from FactGrid and write a raw TSV')
    parser.add_argument('--out',   default=OUT_TSV,
                        help=f'Output TSV (default: {OUT_TSV})')
    parser.add_argument('--limit', type=int, default=None,
                        help='Cap the number of values returned (default: no limit)')
    args = parser.parse_args()

    query = build_query(args.limit)
    print(f'SPARQL query:\n{query}\n')
    limit_msg = f'top {args.limit}' if args.limit else 'all'
    print(f'Querying FactGrid for {limit_msg} distinct P721 values...')

    values = fetch(args.limit)
    print(f'Retrieved {len(values)} values.')

    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    with open(args.out, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter='\t')
        writer.writerow(['value', 'freq'])
        writer.writerows(values)

    print(f'Written: {args.out}')
    print(f'\nNext step: python prop_migration/generate_basis_seed.py --values {args.out}')


if __name__ == '__main__':
    main()
