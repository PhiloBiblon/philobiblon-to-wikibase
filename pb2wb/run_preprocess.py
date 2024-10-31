import argparse

from common import enums
from preprocess import preprocess

parser = argparse.ArgumentParser()
parser.add_argument('--bib', type=str, default="BETA",
                    help="Top-level bib to preprocess. Default: 'BETA'")
parser.add_argument("--table", help="Table to process. Default is process all")
parser.add_argument('--lookup', type=str, default="lookup_pbcog.csv",
                    help="Use a lookup table for q-numbers. Default: 'lookup_pbcog.csv'. Use 'None' to skip lookup.")
parser.add_argument('--instance', type=str, default="PBCOG", help="Instance to use.  Default is PBCOG")

args = parser.parse_args()

if args.instance.lower() not in args.lookup and args.lookup != 'None':
  args.lookup = f'lookup_{args.instance.lower()}.csv'

if args.table:
  args.table = enums.Table[args.table.upper()]

args.bib = enums.Bibliography[args.bib.upper()]

preprocess.preprocess(args.bib, args.table, args.lookup, args.instance)
