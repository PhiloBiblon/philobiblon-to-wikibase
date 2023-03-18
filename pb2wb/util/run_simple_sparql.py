import os
import sys
import argparse

# we assume this script is in a "util" directory
dir_path = os.path.dirname(os.path.realpath(__file__))
parent_dir_path = os.path.dirname(dir_path)

sys.path.append(parent_dir_path)
from common.wb_manager import WBManager

parser = argparse.ArgumentParser()
parser.add_argument('--query', default="SELECT ?item ?value { ?item wdt:P476 ?value } limit 10", help='the sparql to run')
args = parser.parse_args()

wb_manager = WBManager()
results = wb_manager.runSparQlQuery(args.query)
columns = [c for c in results[0]]
print(','.join(columns))

for r in [[r[c]['value'] for c in columns] for r in results]:
    print(','.join(r))
