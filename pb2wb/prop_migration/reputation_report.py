"""
reputation_report.py — summarize FactGrid X-Reputation scores by network and day.

Reads the log written by common/factgrid_access.py. Purely local: no requests.
Name networks by adding "fingerprint<TAB>name" lines to prop_migration/run_logs/networks.tsv.

Usage (from pb2wb/):
    python prop_migration/reputation_report.py
    python prop_migration/reputation_report.py --name home     # label the current network
"""

import argparse
import json
import os
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import common.factgrid_access as fa


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    ap.add_argument('--name', help='label the network you are on now')
    args = ap.parse_args()

    here = fa.network_fingerprint()
    if args.name:
        os.makedirs(os.path.dirname(fa.NETWORKS_TSV), exist_ok=True)
        with open(fa.NETWORKS_TSV, 'a', encoding='utf-8') as f:
            f.write(f'{here}\t{args.name}\n')
        print(f'{here} = {args.name}')
    names = fa.network_names()
    print(f'current network: {names.get(here, here)}\n')

    if not os.path.exists(fa.REPUTATION_LOG):
        print(f'no log yet ({fa.REPUTATION_LOG})')
        return
    groups = defaultdict(list)
    with open(fa.REPUTATION_LOG, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            groups[(names.get(r['network'], r['network']), r['ts'][:10])].append(r)

    print(f"{'network':20} {'day':10} {'reqs':>6} {'min':>8} {'median':>8} {'last':>8} "
          f"{'low':>4} {'chal':>4}")
    for (net, day), rs in sorted(groups.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        reps = [r['reputation'] for r in rs if r['reputation'] is not None]
        fmt = lambda v: f'{v:8.1f}' if v is not None else f"{'-':>8}"
        print(f'{net[:20]:20} {day:10} {len(rs):6} '
              f'{fmt(min(reps) if reps else None)} '
              f'{fmt(statistics.median(reps) if reps else None)} '
              f'{fmt(reps[-1] if reps else None)} '
              f"{sum(r['event'] == 'low' for r in rs):4} "
              f"{sum(r['event'] == 'challenge' for r in rs):4}")


if __name__ == '__main__':
    main()
