import pandas as pd
import sys
import os
import argparse
import datetime
from pathlib import Path

# Get the current date in YYYYMMDD format
date = datetime.datetime.now().strftime("%Y%m%d")

parser = argparse.ArgumentParser()
parser.add_argument('--bib', default='beta', choices=['beta', 'bitagap', 'biteca'], help='Specify a bibliography from the list.  Default is beta.')
parser.add_argument('--instance', default='FACTGRID', choices=['PBCOG', 'FACTGRID'], help='Specify an instance from the list.  Default is PBCOG.')
parser.add_argument('--csv', default='raw', choices=['raw', 'pre'], help='Specify the CSV source to process.  Default is raw data.')
args = parser.parse_args()

bibliography = args.bib.upper()
instance = args.instance.upper()

# Directory path to search for files
directory_path = f'../data/raw/{bibliography}/csvs/'
if args.csv == 'pre':
    directory_path = f'../data/processed/pre/{bibliography}/'

# Find all files in the directory
files = []
for root, _, filenames in os.walk(directory_path):
    for filename in filenames:
        files.append(os.path.join(root, filename))

# Print the list of files
print("Files in directory:", files)

# Create the first_row directory if it does not exist
cwd = os.getcwd()
updated_path = f'{cwd}/first_row/{bibliography}'
Path(f'{updated_path}').mkdir(parents=True, exist_ok=True)

for csv_file_path in files:
    # Extract the string to the right of the first "-"
    file_name = os.path.basename(csv_file_path)
    file_name_parts = file_name.split("-") if args.csv == 'raw' else file_name.split("_")
    if instance.lower() not in file_name and args.csv == 'pre':
        continue
    file_name_parts = [part.strip() for part in file_name_parts]
    print(f'File name parts: {file_name_parts}')
    if args.csv == 'pre':
        extracted_string = file_name_parts[2].split(".")[0]
    else:
        extracted_string = file_name_parts[1]
    print(f'Processing file: {csv_file_path}')
    csv_output_path = f'{updated_path}/{instance.lower()}_{bibliography}_{extracted_string}_first_row_{date}.csv'
    # Read the data from the CSV file
    data = pd.read_csv(csv_file_path)
    # Find the first column name from the CSV
    first_column_name = data.columns[0]
    # Print the id of the first column
    print("First column name:", first_column_name)
    # Extract the 3rd element after the second empty space in the string
    data['id'] = data[first_column_name].str.split(" ").str[2]
    grouped_data = data.groupby(first_column_name).first()
    # Sort the dataframe by the 'id' column
    grouped_data.sort_values('id', inplace=True)
    # Drop the 'id' column
    grouped_data.drop('id', axis=1, inplace=True)
    # Export the grouped data to a new CSV file
    grouped_data.to_csv(csv_output_path)

print(f'Complete. See the updated files in the first_row/{bibliography} directory.')