import argparse
from init import init

parser = argparse.ArgumentParser()
parser.add_argument("--first-time", help="Tries to create untyped properties, i.e, it uses the P number but indeed is not created.", action="store_true")
parser.add_argument("--only-properties", help="Initialize only properties.", action="store_true")
args = parser.parse_args()

init.init(args.first_time, args.only_properties)
