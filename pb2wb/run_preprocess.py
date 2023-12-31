import argparse

from common import enums
from preprocess import preprocess

parser = argparse.ArgumentParser()
parser.add_argument('--bib', type=str, default="BETA",
                    help="Top-level bib to preprocess. Default: 'BETA'")
parser.add_argument("--table", help="Table to process. Default is process all")
parser.add_argument('--lookup', nargs='?', const="lookup.csv", type=str,
                    help="Use a lookup table for q-numbers. Default: 'lookup.csv'")

args = parser.parse_args()

if args.table:
  args.table = enums.Table[args.table.upper()]

preprocess.preprocess(args.bib, args.table, args.lookup)
