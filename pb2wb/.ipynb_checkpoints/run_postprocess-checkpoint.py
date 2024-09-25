import argparse
from postprocess import postprocess
from common import enums

parser = argparse.ArgumentParser()
parser.add_argument("--table", help="Only postprocess this table.")
parser.add_argument("--force-new-statements", help="Forces to create always new statements.", action="store_true")
args = parser.parse_args()

table = None
if args.table:
  table = enums.Table[args.table.upper()]

postprocess.postprocess(table=table, force_new_statements=args.force_new_statements)
