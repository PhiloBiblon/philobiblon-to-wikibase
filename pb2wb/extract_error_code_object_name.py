import pandas as pd
import glob
import argparse
from common.settings import BASE_IMPORT_OBJECTS

parser = argparse.ArgumentParser()
parser.add_argument('--instance', default='PBCOG', choices=['PBCOG', 'FACTGRID'], help='Specify an instance from the list.  Default is PBCOG.')
parser.add_argument('--bibliography', default='beta', choices=['beta', 'bitagap', 'biteca'], help='Bibliography.  Default is beta.')
parser.add_argument('--error', default='dataclip', choices=['dataclip', 'base_object'], help='Error type to search for.  Default')
args = parser.parse_args()

error_QNUM = BASE_IMPORT_OBJECTS[args.instance][f'{args.error.upper()}_RECONCILIATION_ERROR']

def extract_unique_values(df, target_string):
    unique_values = set()
    for index, row in df.iterrows():
        if target_string in row.values:
            index = row.tolist().index(target_string)
            previous_value = row.iloc[index - 1]
            unique_values.add(previous_value)
    return unique_values

def extract_unique_values_from_csvs(table_names):
    target_string = f'{error_QNUM}'
    unique_values = set()
    for table_name in table_names:
        csv_files = glob.glob(f"../data/processed/pre/{args.bibliography.upper()}/{args.instance}_{args.bibliography}_{table_name}.csv")
        for csv_file in csv_files:
            df = pd.read_csv(csv_file)
            unique_values.update(extract_unique_values(df, target_string))

    # Sort the unique values alphabetically
    sorted_values = sorted(unique_values)

    # Write the sorted values to a file
    with open(f'unique_{args.error}_errors_{args.instance}_{args.bibliography}.txt', "w") as f:
        sorted
        for value in sorted_values:
            f.write(f"{value}\n")

    matching_rows = find_rows_with_multiple_matches(df, target_string)
    # Create a new DataFrame from the matching rows
    matching_df = pd.DataFrame(matching_rows)

    # Write the DataFrame to a CSV file
    matching_df.to_csv(f'multiple_{args.error}_row_matches_{args.instance}_{args.bibliography}.csv', index=False)

    return sorted_values

def find_rows_with_multiple_matches(df, target_string):
    matching_rows = []
    for index, row in df.iterrows():
        if row.str.contains(target_string).sum() > 1:
            matching_rows.append(row)
    return matching_rows

# Table names
table_names = ['analytic', 'biography', 'geography', 'institutions', 'library', 'subject', 'bibliography', 'copies', 'ms_ed', 'uniform_title']

# Extract unique values from all CSV files
unique_values = extract_unique_values_from_csvs(table_names)

print(unique_values)