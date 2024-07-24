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
updated_path = f'{cwd}/updated/{bibliography}'
Path(f'{updated_path}').mkdir(parents=True, exist_ok=True)

files = [f'{bibliography}_analytic.csv', f'{bibliography}_biography.csv', f'{bibliography}_geography.csv', f'{bibliography}_institutions.csv',
         f'{bibliography}_library.csv', f'{bibliography}_subject.csv', f'{bibliography}_bibliography.csv', f'{bibliography}_copies.csv',
         f'{bibliography}_institutions.csv', f'{bibliography}_ms_ed.csv', f'{bibliography}_uniform_title.csv']

def perform_inner_join(input_file, updated_df, output_file, first_column_name):
    # Read the input csv file
    input_df = pd.read_csv(input_file)
    
    # Perform inner join with the updated dataframe
    result = pd.merge(input_df, updated_df, on=[first_column_name], how='inner')
    
    # Write the result to the output csv file
    result.to_csv(output_file, index=False)

for file in files:
    print(f'Processing file: {file}')
    input_file = '../data/clean/' + str.upper(f'{bibliography}') + f'/csvs/{file}'
    output_file = f'{updated_path}/{file}'
    print(f'Using input file: {file}')
    pre_df = pd.read_csv('../data/processed/pre/' + str.upper(f'{bibliography}') + f'/{file}')
    first_column_name = pre_df.columns[0]

    # Search qnum value that represents the BASE_OBJECT_RECONCILIATION_ERROR
    search_string = BASE_IMPORT_OBJECTS['PBCOG']['BASE_OBJECT_RECONCILIATION_ERROR']
    print(f'Filtering against string: {search_string}')
    filtered_df = pre_df[pre_df.eq(search_string).any(axis=1)]

    # Select unique id values from the filtered dataframe
    updated_df = filtered_df.loc[:, [first_column_name]].drop_duplicates()

    # Launch join operation
    perform_inner_join(input_file, updated_df, output_file, first_column_name)
