import csv
import argparse
import re
from googletrans import Translator

parser = argparse.ArgumentParser()
parser.add_argument('--csv_filepath', type=str, help="path to the input CSV file", required=True)
parser.add_argument('--output_filepath', type=str, help="path to the output QuickStatements file", required=True)
parser.add_argument('--item_column', type=str, default='item', help="column name for the item QIDs", required=False)
parser.add_argument('--value_column', type=str, default='alias', help="column name for the values", required=False)
parser.add_argument('--value_clean', help='If present, extract QNUM form url', action='store_true')
parser.add_argument('--property_pid', help='property pid to use', required=True)
parser.add_argument('--delete', help="If present, append '-' to statement to delete", action='store_true')
parser.add_argument('--labels', help="If present, extract label and description from value column", action='store_true')
parser.add_argument('--translate', action='store_true', help="If present, translate the label value to English")
args = parser.parse_args()

csv_file = args.csv_filepath
output_file = args.output_filepath
property_pid = args.property_pid

# Example SPARQL query to fetch bio objects with BETA bioid and label
'''
SELECT ?item ?itemLabel ?itemDescription ?pbid
WHERE {
  ?item wdt:P476 ?pbid.
  FILTER CONTAINS(STR(?pbid), "BETA bioid")
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
'''

def translate(text, target_language='en'):
    """Translate a value to a different language (en) using the Google Translate API.
    """
    try:
        translator = Translator()
        print(f"Translating: {text}")
        translation = translator.translate(text, src='es', dest=target_language)
        return translation.text
    except Exception as e:
        print(f"Translation error: {e}")
        return None

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
                if args.value_clean:
                    clean = re.search(r'/(Q\d+)', value)
                    if clean:
                        value = clean.group(1)
                    else:
                        print(f"Warning: QNUM not found in value: {value}")
                        continue
                else:
                    value = f'\"{value}\"'  # Wrap value in double quotes
                # Extract QNUM from URL using regular expression
                match = re.search(r'/(Q\d+)', item_qid)
                if match:
                    item_qid = match.group(1)  # Group 1 captures the QNUM
                else:
                    print(f"Warning: QNUM not found in item URL: {item_qid}")
                    continue  # Skip rows where QNUM cannot be extracted
                if value: #Skips empty values
                    if args.delete:
                        if args.labels:
                            split_value = value.split(',', 1)
                            if len(split_value) > 1:
                                label = f'{split_value[0]}\"'
                                description = f'\"{split_value[1].lstrip()}'
                                outfile.write(f"-{item_qid}|Les|{label}\n")  #Adjust for language as needed: Les = label (spanish)
                                outfile.write(f"-{item_qid}|Des|{description}\n")
                                if args.translate:
                                    label = translate(label)
                                    description = translate(description)
                                #outfile.write(f"-{item_qid}|Len|{label}\n")
                                #outfile.write(f"-{item_qid}|Den|{description}\n")
                                continue
                        outfile.write(f"-{item_qid}|{property_pid}|{value}\n") # Append '-' to delete statement
                    else:
                        if args.labels:
                            split_value = value.split(',', 1)
                            if len(split_value) > 1:
                                label = f'{split_value[0]}\"'
                                description = f'\"{split_value[1].lstrip()}'
                                outfile.write(f"{item_qid}|Les|{label}\n") #Adjust for language as needed: Les = label (spanish)
                                outfile.write(f"{item_qid}|Des|{description}\n")
                                if args.translate:
                                    label = translate(label)
                                    description = translate(description)
                                #outfile.write(f"{item_qid}|Len|{label}\n")
                                #outfile.write(f"{item_qid}|Den|{description}\n")
                                continue
                        outfile.write(f"{item_qid}|{property_pid}|{value}\n")
    except FileNotFoundError:
        print(f"Error: Input file '{csv_filepath}' not found.")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

csv_to_quickstatements(csv_file, output_file, property_pid)
