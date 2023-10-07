import argparse
from init import init

parser = argparse.ArgumentParser()
parser.add_argument("--only-properties", help="Initialize only properties.", action="store_true")
parser.add_argument("--only-qitems", help="Initialize only qitems.", action="store_true")
args = parser.parse_args()

init.init(args.only_properties, args.only_qitems)
