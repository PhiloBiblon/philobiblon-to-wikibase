import argparse
from notes import notes
from common import enums

parser = argparse.ArgumentParser()
parser.add_argument('--table', help='Only preprocess this table.')
args = parser.parse_args()

if args.table:
  notes.add_notes(enums.Table[args.table.upper()])
else:
  notes.add_notes(None)

print('done.')