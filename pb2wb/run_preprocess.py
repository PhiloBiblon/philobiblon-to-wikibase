import argparse
from preprocess import preprocess
from common import enums

parser = argparse.ArgumentParser()
parser.add_argument("--table", help="Only preprocess this table.")
args = parser.parse_args()

preprocess.preprocess(enums.Table[args.table.upper()])
