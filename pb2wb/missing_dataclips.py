from common.data_dictionary import DATADICT
import argparse
import pandas as pd

bibliographies = ['beta', 'bitagap', 'biteca']
instances = ['LOCAL_WB', 'PBSANDBOX', 'PBCOG', 'FACTGRID']
tables = ['analytic', 'biography', 'geography', 'institutions', 'library', 'subject', 'bibliography', 'copies', 'ms_ed', 'uniform_title']

parser = argparse.ArgumentParser()
parser.add_argument('--bib', default='beta', choices=bibliographies, help='Specify a bibliography from the list.  Default is beta.')
parser.add_argument('--instance', default='PBCOG', choices=instances, help='Specify a instance from the list.  Default is pbcog.')
parser.add_argument('--table', default='all', choices=tables, help='Specify a table from the list.  Default is all.')

args = parser.parse_args()
bibliography = args.bib.lower()
instance = args.instance.lower()

if args.table == 'all':
    tables = tables
else:
    tables = [args.table]

lookup_csv = f'../data/clean/{bibliography.upper()}/lookup_{instance}.csv'
output_csv = f'{bibliography.upper()}_missing_dataclips_{instance}.csv'
df = pd.read_csv(lookup_csv)

all_clips = []

for table in tables:
    print(f'Checking {table} dataclips')
    for key, value in DATADICT.items():
        if table.upper() in key:
            input_csv = f'../data/processed/pre/{bibliography.upper()}/{instance.lower()}_{bibliography.lower()}_{table.lower()}.csv'
            dataclips = DATADICT[table.upper()]['dataclip_fields']
            print(f'{dataclips = }')

            for clip in dataclips:
                print(f'Checking {clip}')
                df2 = pd.read_csv(input_csv)
                clips_new = df2[clip].drop_duplicates().dropna()
                all_clips.append(clips_new)

# Concatenate DataFrames
clips_df = pd.concat(all_clips, ignore_index=True)

# Filter for strings, droping NaN and dropping duplicates
clips_df = clips_df[clips_df.apply(lambda row: all(isinstance(x, str) for x in row))]
clips_df = clips_df.drop_duplicates()

# Compare clips against lookup table and save missing items
missing_items = clips_df[~clips_df.isin(df['QNUMBER'])]
print(f'{missing_items = }')
missing_items.to_csv(output_csv, index=False, mode='a', header=False)