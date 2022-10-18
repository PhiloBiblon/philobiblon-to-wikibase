import argparse
from postprocess import postprocess
from common import enums

parser = argparse.ArgumentParser()
parser.add_argument("--table", help="Only preprocess this table.")
args = parser.parse_args()

if args.table:
  postprocess.postprocess(enums.Table[args.table.upper()])
else:
  postprocess.postprocess(None)
