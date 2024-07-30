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
    input_file = f'../data/clean/{bibliography.upper()}/csvs/{file}'
    output_file = f'{updated_path}/{file}'
    print(f'Using input file: {input_file}')
    pre_df = pd.read_csv(input_file)
  
    # Select the first column from the pre_df dataframe
    first_column = pre_df.iloc[:, 0]

    # Get the unique values from the first column
    unique_ids = first_column.unique()

    # Select the first 10 unique ids
    selected_ids = unique_ids[:10]

    # Filter the pre_df dataframe based on the selected ids and write to a new csv file
    filtered_df = pre_df[pre_df.iloc[:, 0].isin(selected_ids)]
    filtered_df.to_csv(output_file, index=False)

print(f'Complete. See the updated files in the spot_test/{bibliography} directory.')
