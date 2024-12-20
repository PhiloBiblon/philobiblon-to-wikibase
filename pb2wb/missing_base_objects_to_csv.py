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
parser.add_argument('--table', default='all', choices=tables, help='Specify a table from the list for base_object error check.  Default is all.')
parser.add_argument('--error', default='dataclip', choices=['dataclip', 'base_object'], help='Error type to search for.  Default')
args = parser.parse_args()

bibliography = args.bib.lower()
instance = args.instance.lower()
table = args.table
error_QNUM = BASE_IMPORT_OBJECTS[args.instance][f'{args.error.upper()}_RECONCILIATION_ERROR']
files = []

# Get the current working directory
cwd = os.getcwd()

# Create the updated directory if it does not exist
updated_path = f'{cwd}/updated/{bibliography}'
Path(f'{updated_path}').mkdir(parents=True, exist_ok=True)

# If dataclip is selected, use the dataclip path
if args.error == 'dataclip':
    updated_path = f'errors/dataclip'
    Path(f'{updated_path}').mkdir(parents=True, exist_ok=True)

if table == 'all':
    for table in tables:
        files.append(f'{bibliography}_{table}.csv')
else:
    files = [f'{bibliography}_{table}.csv']

print(f'Files to process: {files}')

def perform_inner_join(input_file, updated_df, output_file, first_column_name):
    # Read the input csv file
    input_df = pd.read_csv(input_file)
    
    # Perform inner join with the updated dataframe
    result = pd.merge(input_df, updated_df, on=[first_column_name], how='inner')
    
    # Write the result to the output csv file
    print(f'Writing to output file: {output_file}')
    result.to_csv(output_file, index=False)

def search_and_update_dataframe(df, search_string):
    # Check if the DataFrame is empty
    if df.empty:
        return df

    # Initialize an empty list to store the results
    results = []

    # Iterate over each row in the DataFrame and search for the string
    for index, row in df.iterrows():
        for col_index in range(1, len(row)):
            if search_string in str(row.iloc[col_index]):
                # Check if the preceding value is 'und'
                if row.iloc[col_index - 1] == 'und':
                    if col_index >= 2: #Check to make sure index is not out of range
                        results.append([row.iloc[0], row.iloc[col_index - 2]])
                    else:
                        results.append([row.iloc[0], None]) # Append None if index is out of range
                else:
                    results.append([row.iloc[0], row.iloc[col_index - 1]])
                break  # Important: Exit the inner loop once a match is found

    if results: #Check if results is not empty
        updated_df = pd.DataFrame(results, columns=[df.columns[0], 'Dataclip']) # Create a new DataFrame with the results
        updated_df = updated_df.drop(columns=[df.columns[0]]) # Drop the first column
        updated_df = updated_df.drop_duplicates() # Drop duplicates
        return updated_df
    else:
        return pd.DataFrame(columns=[df.columns[0], 'Dataclip']) # Return empty dataframe with correct columns

all_filtered_dfs = []

for file in files:
    input_file = f'../data/clean/{bibliography.lower()}/csvs/{file}'
    output_file = f'{updated_path}/{instance}_{file}'
    print(f'Using input file: {file}')
    pre_df = pd.read_csv(f'../data/processed/pre/{bibliography.upper()}/{instance}_{file}')
    first_column_name = pre_df.columns[0]

    # Search qnum value that represents the BASE_OBJECT_RECONCILIATION_ERROR
    search_string = error_QNUM
    print(f'Filtering against string: {search_string}')
    if args.error == 'dataclip':
        filtered_df = search_and_update_dataframe(pre_df, search_string)
        all_filtered_dfs.append(filtered_df)  # Append to the list
        continue
    else:
        filtered_df = pre_df[pre_df.iloc[:, 1].eq(search_string)]

    # Select unique id values from the filtered dataframe
    updated_df = filtered_df.loc[:, [first_column_name]].drop_duplicates()

    # Launch join operation
    perform_inner_join(input_file, updated_df, output_file, first_column_name)

    # Concatenate all filtered dataclip error into a single DataFrame
if all_filtered_dfs: #Check if list is not empty
    final_df = pd.concat(all_filtered_dfs, ignore_index=True)
    final_output_file = os.path.join(updated_path, f'combined_dataclip_errors_{args.instance}_{args.bib}.csv') #Create combined output file path
    print(f'Writing combined output to: {final_output_file}')
    final_df.to_csv(final_output_file, index=False)
else:
    print("No error matches found in any file.")
