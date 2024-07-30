import pandas as pd
import sys
import os
import argparse
import datetime
from pathlib import Path

# Get the current date in YYYYMMDD format
date = datetime.datetime.now().strftime("%Y%m%d")

# Parse command line arguments for bibliography
bibliographies = ['beta', 'bitagap', 'biteca']

parser = argparse.ArgumentParser()
parser.add_argument('--bib', default='beta', choices=bibliographies, help='Specify a bibliography from the list.  Default is beta.')
args = parser.parse_args()

bibliography = args.bib.upper()

# Directory path to search for files
directory_path = f'../data/raw/{bibliography}/csvs/'

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
    file_name_parts = file_name.split("-")
    file_name_parts = [part.strip() for part in file_name_parts]
    extracted_string = file_name_parts[1]
    print(f'Processing file: {csv_file_path}')
    csv_output_path = f'{updated_path}/{bibliography}_{extracted_string}_first_row_{date}.csv'
    # Read the data from the CSV file
    data = pd.read_csv(csv_file_path)
    # Find the first column name from the CSV
    first_column_name = data.columns[0]
    # Print the output
    print("First column name:", first_column_name)
    # Group the data by "MANID" column and export to csv
    grouped_data = data.groupby(first_column_name).first()
    grouped_data.to_csv(csv_output_path)

print(f'Complete. See the updated files in the first_row/{bibliography} directory.')