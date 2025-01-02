import csv
import argparse
import re

parser = argparse.ArgumentParser()
parser.add_argument('--csv_filepath', type=str, help="path to the input CSV file", required=True)
parser.add_argument('--output_filepath', type=str, help="path to the output QuickStatements file", required=True)
parser.add_argument('--item_column', type=str, default='item', help="column name for the item QIDs", required=False)
parser.add_argument('--value_column', type=str, default='alias', help="column name for the values", required=False)
parser.add_argument('--property_pid', help='property pid to use', required=True)
args = parser.parse_args()

csv_file = args.csv_filepath
output_file = args.output_filepath
property_pid = args.property_pid

def csv_to_quickstatements(csv_filepath, output_filepath, property_pid, item_column=args.item_column, value_column=args.value_column):
    """Converts a CSV file to QuickStatements format with only item, property, and value.
    """
    try:
        with open(csv_filepath, 'r', encoding='utf-8') as infile, open(output_filepath, 'w', encoding='utf-8') as outfile:
            reader = csv.DictReader(infile)
            if item_column not in reader.fieldnames:
                raise ValueError(f"'{item_column}' column not found in CSV")
            if value_column not in reader.fieldnames:
                raise ValueError(f"'{value_column}' column not found in CSV")
            for row in reader:
                item_qid = row[item_column]
                value = row[value_column]
                # Extract QNUM from URL using regular expression
                match = re.search(r'/(Q\d+)', item_qid)
                if match:
                    item_qid = match.group(1)  # Group 1 captures the QNUM
                else:
                    print(f"Warning: QNUM not found in item URL: {item_qid}")
                    continue  # Skip rows where QNUM cannot be extracted
                if value: #Skips empty values
                    outfile.write(f"{item_qid}|{property_pid}|\"{value}\"\n")
    except FileNotFoundError:
        print(f"Error: Input file '{csv_filepath}' not found.")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

csv_to_quickstatements(csv_file, output_file, property_pid)
