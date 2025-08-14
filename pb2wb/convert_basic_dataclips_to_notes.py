import pandas as pd
import argparse
from common.settings import TEMP_DICT
import os
import time


def parse_replacement(pair):
    if ':' not in pair:
        raise argparse.ArgumentTypeError("Replacement must be in format 'old:new'")
    old, new = pair.split(':', 1)
    return {old.strip(): new.strip()}

parser = argparse.ArgumentParser()
parser.add_argument('--instance', default='PBCOG')
parser.add_argument('--bib', default='beta')
parser.add_argument('--table', required=True)
parser.add_argument('--dry_run', action='store_true')
parser.add_argument('--alt_csv', type=str)
parser.add_argument('--limit', type=int)
parser.add_argument('--replace', type=parse_replacement)
parser.add_argument('--reset_notes', action='store_true', help='Reset existing notes if set')

args = parser.parse_args()

instance = parser.parse_args().instance
bibliography = parser.parse_args().bib
table = parser.parse_args().table
dry_run = parser.parse_args().dry_run
reset_notes = parser.parse_args().reset_notes
alt_csv = parser.parse_args().alt_csv
limit = parser.parse_args().limit
replace = parser.parse_args().replace
print(replace)

# Set the TEMP_DICT for the instance and bibliography
TEMP_DICT['TEMP_WB'] = instance.upper()
print(f"Using instance: {TEMP_DICT['TEMP_WB']}")
if reset_notes:
    print(f"Reset notes has been set to {reset_notes}.  This will reset the notes for the given instance and bibliography.")
    TEMP_DICT['RESET'] = reset_notes

language_columns = {'BETA': 'es', 'BITECA': 'ca', 'BITAGAP': 'pt'}

HEADERS = {
    'BETA': '=== BETA / Bibliografía Española de Textos Antiguos ===',
    'BITECA': '=== BITECA / Bibliografia de Textos Antics Catalans, Valencians i Balears ===',
    'BITAGAP': '=== BITAGAP / Bibliografia de Textos Antigos Galegos e Portugueses ==='
}
MAPPINGS = {
    'BETA': {
        'NOTES': {
            'COLUMN': 'NOTES',
            'TOPIC': '== Notas ==',
            'NOTES': ''
        }
    },
    'BITECA': {
        'NOTES': {
            'COLUMN': 'NOTES',
            'TOPIC': '== Notas ==',
            'NOTES': ''
        }
    },
    'BITAGAP': {
        'NOTES': {
            'COLUMN': 'NOTES',
            'TOPIC': '== Notas ==',
            'NOTES': ''
        }
    }
}

header = HEADERS[args.bib.upper()]
mapping = MAPPINGS[args.bib.upper()]['NOTES']

# Load the data
if args.alt_csv:
    df = pd.read_csv(args.alt_csv, low_memory=False)
else:
    df = pd.read_csv(f"../data/processed/pre/{args.bib}/{args.instance}_{args.bib}_{args.table}.csv", low_memory=False)

# dataframes for BETA and BITECA
beta_file = f'../data/processed/pre/BETA/{instance}_beta_{table}.csv'
biteca_file = f'../data/processed/pre/BITECA/{instance}_biteca_{table}.csv'
beta_df = pd.read_csv(f'{beta_file}', low_memory=False)
biteca_df = pd.read_csv(f'{biteca_file}', low_memory=False)

# Only keep necessary columns
failed_qnums = []
first_column = df.columns[0] # PBID
second_column = df.columns[1] # QNUMBER
required_columns = [second_column, mapping['COLUMN']]
df = df[required_columns].dropna(subset=[mapping['COLUMN']])

# Format the notes
df['Formatted_Notes'] = df[mapping['COLUMN']].apply(
    lambda x: f"{mapping['TOPIC']}\n{str(x).strip()}" if str(x).strip() else '')

def post_notes(q_number, text):
    retry_count = 0
    max_retries = 3  # Maximum number of retries for posting notes
    from notes import notes
    print(f"Adding notes for {q_number} into talk page..")
    print(f"Notes: {text}")
    if replace:
        print(f"Attempting to apply text replacements: {replace}")
        notes.add_append_talk_page_notes(q_number, text, reset=reset_notes, replacement_map=replace)
        return  # Exit after applying replacements
    if reset_notes and bibliography.upper() in ['BITECA', 'BITAGAP']:
        print(f"Checking if qnum is shared between {bibliography} and BETA")
        # Check if the QNUMBER is shared between BITECA/BITAGAP and BETA
        if bibliography.upper() == 'BITECA' or bibliography.upper() == 'BITAGAP':
            exists = q_number in beta_df[second_column].values
        elif bibliography.upper() == 'BITAGAP':
            exists = q_number in biteca_df[second_column].values
        if exists:
            print(f"Found shared QNUMBER {q_number} in BETA, skipping reset.")
            return # Skip resetting notes if shared with BETA
    while retry_count < max_retries:
        try:
            notes.add_append_talk_page_notes(q_number, text, reset=reset_notes, replacement_map=None)  # Use the notes module to add or reset notes
            print(f"Successfully posted notes for {q_number}")
            break  # Exit loop if successful
        except Exception as e:
            retry_count += 1
            print(f"Error posting notes for {q_number}: {e}. Retrying {retry_count}/{max_retries}")
            time.sleep(30)  # Wait before retrying
    if retry_count == max_retries:
        print(f"Failed to post notes for {q_number} after {max_retries} attempts. Skipping this QNUMBER.")
        failed_qnums.append(q_number)  # Keep track of failed QNUMs


# Build output
output = {}
for _, row in df.iterrows():
    qnum = row[second_column]
    note = f"{header}\n{row['Formatted_Notes']}"
    if args.replace:
        for old, new in args.replace.items():
            note = note.replace(old, new)
    output[qnum] = note

# Output
for i, (qnum, text) in enumerate(output.items()):
    if args.dry_run:
        print(f"[DRY RUN] Would post to {qnum}:\n{text}\n")
    else:
        print(f"Processing {qnum}")
        post_notes(qnum, text)
    if args.limit and i + 1 >= args.limit:
        break

# Print failed QNUMs if any
print(f'Failed QNUMs: {failed_qnums}') if 'failed_qnums' in locals() else print('No failed QNUMs.')
