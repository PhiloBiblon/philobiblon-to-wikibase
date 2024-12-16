import pandas as pd
import argparse
import csv
import os


parser = argparse.ArgumentParser()
parser.add_argument('--instance', default='PBCOG', choices=['PBCOG', 'FACTGRID'], help='Specify an instance from the list.  Default is PBCOG.')
parser.add_argument('--column', default='PBID', help='Column to check for duplicates.  Default is PBID.')
parser.add_argument('--dupe-only', action='store_true', help='Only perform duplicate check and print results.')
args = parser.parse_args()

username = os.environ.get('USER')
print(f"Current username: {username}")

# Define the input and output file paths
input_file = f'/Users/{username}/Downloads/query.csv' #Download from OR default location with default name query.csv
output_file = f'../data/lookup_{args.instance.lower()}.csv'

base_url = 'database.factgrid.de'
if args.instance == 'PBCOG':
    base_url = 'philobiblon.cog.berkeley.edu'
full_url = f'https://{base_url}/entity/'

# Check for inmput file
if not os.path.exists(input_file):
    raise FileNotFoundError(f"Input file not found: {input_file}")

def process_lookup_csv():

    # Open the input and output files
    with open(input_file, "r") as infile, open(output_file, "w", newline="") as outfile:

        # Create reader and writer objects
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
 
        # Process each row
        for row in reader:
            # Replace URL pattern
            for i, cell in enumerate(row):
                row[i] = cell.replace(f'{full_url}', "")

            # Remove prefixes from the first column
            prefixes_to_remove = ['ORD:', 'PRO:', 'REL:']
            for prefix in prefixes_to_remove:
                row[0] = row[0].replace(prefix, "")

            if row[1].startswith('https:'):
                print(f"Error: No replacement made for cell: {cell}, check URL pattern.")
                raise ValueError("Replacement failed. Aborting processing.")
            
            # Write modified row to the output file
            writer.writerow(row)
        
        print(f"Lookup file created: {output_file}")

def find_duplicates_in_column(csv_file, column_name):
    #Finds and prints duplicate values in a specified column of a CSV file.

    df = pd.read_csv(csv_file)

    # Find duplicate values in the specified column
    duplicates = df[df.duplicated(subset=[column_name], keep=False)]

    # Print the duplicate values
    if not duplicates.empty:
        print(f"Duplicate values found in column '{column_name}':")
        print(duplicates)
    else:
        print(f"No duplicates found in column '{column_name}'.")

# Input CSV file and column name
if not args.dupe_only:
    print('creating lookup file: ', output_file)
    process_lookup_csv()
find_duplicates_in_column(output_file, column_name=args.column)