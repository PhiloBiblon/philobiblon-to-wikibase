import csv
import pandas as pd
from common.settings import BASE_IMPORT_OBJECTS

files = ['beta_analytic.csv', 'beta_biography.csv', 'beta_geography.csv', 'beta_library.csv', 'beta_subject.csv',      
          'beta_bibliography.csv', 'beta_copies.csv', 'beta_institutions.csv', 'beta_ms_ed.csv', 'beta_uniform_title.csv']

def perform_inner_join(input_file, updated_df, output_file, first_column_name):
    # Read the input csv file
    input_df = pd.read_csv(input_file)
    
    # Perform inner join with the updated dataframe
    result = pd.merge(input_df, updated_df, on=[first_column_name], how='inner')
    
    # Write the result to the output csv file
    result.to_csv(output_file, index=False)

for file in files:
    print(f'Processing file: {file}')
    input_file = f'../data/clean/BETA/csvs/{file}'
    output_file = f'updated_{file}'
    print(f'Using input file: {file}')
    pre_df = pd.read_csv(f'../data/processed/pre/BETA/{file}')
    first_column_name = pre_df.columns[0]

    # Search qnum value that represents the BASE_OBJECT_RECONCILIATION_ERROR
    search_string = BASE_IMPORT_OBJECTS['PBCOG']['BASE_OBJECT_RECONCILIATION_ERROR']
    print(f'Filtering against string: {search_string}')
    filtered_file = f'filtered_{file}'
    filtered_df = pre_df[pre_df.eq(search_string).any(axis=1)]

    # Select unique id values from the filtered dataframe
    updated_df = filtered_df.loc[:, [first_column_name]].drop_duplicates()

    # Launch join operation
    perform_inner_join(input_file, updated_df, output_file, first_column_name)
