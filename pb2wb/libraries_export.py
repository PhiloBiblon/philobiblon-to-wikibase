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
file_path = f'../data/clean/{bibliography}/csvs/{bibliography.lower()}_library.csv'

# Read the CSV file into a pandas DataFrame
df = pd.read_csv(file_path)

# Extract the desired columns
columns = ['NAME', 'ADDRESS', 'CITY', 'STATE', 'COUNTRY', 'PCODE']
df_extracted = df[columns]

# Export the extracted DataFrame to a new CSV file
extracted_path = f'../data/extracted/'
Path(f'{extracted_path}').mkdir(parents=True, exist_ok=True)
output_file_path = f'{extracted_path}{bibliography.lower()}_extracted_populated.csv'

# Export the extracted DataFrame to a new CSV file
df_extracted_populated = df_extracted[df_extracted['CITY'].notnull()]
df_extracted_populated.to_csv(output_file_path, index=False)

# Print the path of the output file
print(f"Data exported to: {output_file_path}")

