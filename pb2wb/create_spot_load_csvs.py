import csv
import pandas as pd
from common.settings import BASE_IMPORT_OBJECTS
from pathlib import Path
import argparse
import os


# Parse command line arguments for bibliography
bibliographies = ['beta', 'bitagap', 'biteca']

parser = argparse.ArgumentParser()
parser.add_argument('--bib', default='beta', choices=bibliographies, help='Specify a bibliography from the list.  Default is beta.')
args = parser.parse_args()

bibliography = args.bib.lower()

# Get the current working directory
cwd = os.getcwd()

# Create the updated directory if it does not exist
updated_path = f'{cwd}/spot_test/{bibliography}'
Path(f'{updated_path}').mkdir(parents=True, exist_ok=True)

files = [f'{bibliography}_analytic.csv', f'{bibliography}_biography.csv', f'{bibliography}_geography.csv', f'{bibliography}_institutions.csv', \
         f'{bibliography}_library.csv', f'{bibliography}_subject.csv', f'{bibliography}_bibliography.csv', f'{bibliography}_copies.csv', \
         f'{bibliography}_institutions.csv', f'{bibliography}_ms_ed.csv', f'{bibliography}_uniform_title.csv']

for file in files:
    print(f'Processing file: {file}')
    input_file = f'../data/clean/{bibliography.lower()}/csvs/{file}'
    output_file = f'{updated_path}/{file}'
    print(f'Using input file: {file}')
    pre_df = pd.read_csv(f'../data/processed/pre/{bibliography.upper()}/{file}')
  
    # Select the first 10 rows from the pre_df dataframe
    first_10_rows = pre_df.head(10)

    # Write the first 10 rows to a new CSV file
    first_10_rows.to_csv(output_file, index=False)

print(f'Complete. See the updated files in the spot_test/{bibliography} directory.')
