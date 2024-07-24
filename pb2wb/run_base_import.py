from base_import import base_import

import argparse

from common import enums

parser = argparse.ArgumentParser()
parser.add_argument('--bib', type=str, default="BETA",
                    help="Top-level bib to preprocess. Default: 'BETA'")
parser.add_argument('--skip_existing', action='store_true',
                    help='Skip any objects that already exist')
parser.add_argument('--dry_run', action='store_true',
                    help='Dry run: do not side-effect the wikibase')
parser.add_argument('--sample_size', type=int, default=0,
                    help='Specify the sample size as a positive integer (default: 0 means process all)')
parser.add_argument("--table", help="Table to process. Default is process all")
parser.add_argument('--updated', action='store_false', help="Process missing objects. Default is false")
args = parser.parse_args()

if args.table:
  args.table = enums.Table[args.table.upper()]

base_import.base_import(bib=args.bib, table=args.table,
                        skip_existing=args.skip_existing, dry_run=args.dry_run,
                        sample_size=args.sample_size, updated=args.updated)
