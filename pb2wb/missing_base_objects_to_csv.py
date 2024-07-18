import csv
import subprocess
import pandas as pd

files = ['beta_analytic.csv', 'beta_biography.csv', 'beta_geography.csv', 'beta_library.csv', 'beta_subject.csv',      
          'beta_bibliography.csv', 'beta_copies.csv', 'beta_institutions.csv', 'beta_ms_ed.csv', 'beta_uniform_title.csv']

def perform_bash_command(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    print(result.stdout)
    result_list = result.stdout.split('\n')
    return result_list

def perform_inner_join(input_file, string_list, output_file):
    # Read the input csv file
    df = pd.read_csv(input_file)
    
    # Perform inner join with the string list
    first_column_name = df.columns[0]
    result = df[df[first_column_name].isin(string_list)]
    
    # Write the result to the output csv file
    result.to_csv(output_file, index=False)

for file in files:
    print(file)
    command = f'cat ../data/processed/pre/BETA/{file} | grep Q51453 | csvcut -c1 | sort | uniq'
    output = perform_bash_command(command)
    print(output)
    input_file = f'../data/clean/BETA/csvs/{file}'
    output_file = f'test_{file}'
    search_string = output
    perform_inner_join(input_file, search_string, output_file)