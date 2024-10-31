import csv
import pandas as pd
from common.settings import BASE_IMPORT_OBJECTS
from pathlib import Path
import argparse
import os


# Parse command line arguments for bibliography
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
table = args.table

# Get the current working directory
cwd = os.getcwd()

# Create the updated directory if it does not exist
updated_path = f'{cwd}/updated/{bibliography}'
Path(f'{updated_path}').mkdir(parents=True, exist_ok=True)

if table == 'all':
    for table in tables:
        files = [f'{bibliography}_{table}.csv']
else:
    files = [f'{bibliography}_{table}.csv']

def perform_inner_join(input_file, updated_df, output_file, first_column_name):
    # Read the input csv file
    input_df = pd.read_csv(input_file)
    
    # Perform inner join with the updated dataframe
    result = pd.merge(input_df, updated_df, on=[first_column_name], how='inner')
    
    # Write the result to the output csv file
    print(f'Writing to output file: {output_file}')
    result.to_csv(output_file, index=False)

for file in files:
    print(f'Processing file: {file}')
    input_file = f'../data/clean/{bibliography.lower()}/csvs/{file}'
    output_file = f'{updated_path}/{instance}_{file}'
    print(f'Using input file: {file}')
    pre_df = pd.read_csv(f'../data/processed/pre/{bibliography.upper()}/{instance}_{file}')
    first_column_name = pre_df.columns[0]

    # Search qnum value that represents the BASE_OBJECT_RECONCILIATION_ERROR
    search_string = BASE_IMPORT_OBJECTS[instance.upper()]['BASE_OBJECT_RECONCILIATION_ERROR']
    print(f'Filtering against string: {search_string}')
    filtered_df = pre_df[pre_df.iloc[:, 1].eq(search_string)]

    # Select unique id values from the filtered dataframe
    updated_df = filtered_df.loc[:, [first_column_name]].drop_duplicates()

    # Launch join operation
    perform_inner_join(input_file, updated_df, output_file, first_column_name)
