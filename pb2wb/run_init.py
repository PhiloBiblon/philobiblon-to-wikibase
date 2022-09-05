import argparse
from init import init

parser = argparse.ArgumentParser()
parser.add_argument("--firsttime", help="Tries to create untyped properties, i.e, it uses the P number but indeed is not created.", action="store_true")
args = parser.parse_args()

init.init(args.firsttime)
