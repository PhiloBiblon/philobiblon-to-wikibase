import argparse
from common import enums
from common.settings import TEMP_DICT

parser = argparse.ArgumentParser()
parser.add_argument('--table', help='Only preprocess this table.')
parser.add_argument('--instance', default='PBCOG', help='Instance to use. Default is PBCOG.')
parser.add_argument('--bib', default='beta', help='bibliography to be processed, default is beta.')
args = parser.parse_args()

TEMP_DICT['TEMP_WB'] = args.instance.upper()
TEMP_DICT['TEMP_BIB'] = args.instance.upper()

from notes import notes
if args.table:
  notes.add_notes(enums.Table[args.table.upper()], args.bib.upper())
else:
  notes.add_notes(None)

print('done.')