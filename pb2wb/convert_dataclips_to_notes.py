import pandas as pd
import argparse
from common.settings import TEMP_DICT
import os
import glob

parser = argparse.ArgumentParser()
parser.add_argument('--instance', default='PBCOG', choices=['PBCOG', 'FACTGRID'], help='Specify an instance from the list.  Default is PBCOG.')
parser.add_argument('--bib', default='beta', choices=['beta', 'bitagap', 'biteca'], help='Bibliography.  Default is beta.')
parser.add_argument('--filetype', default='text', choices=['text', 'html'], help='File type to output.  Default is text.')
parser.add_argument('--table', help="Table to process", choices=['analytic', 'biography', 'geography', 'institutions', 'library', 'subject', 'bibliography', 'copies', 'ms_ed', 'uniform_title'], required=True)

instance = parser.parse_args().instance
bibliography = parser.parse_args().bib
filetype = parser.parse_args().filetype
table = parser.parse_args().table
TEMP_DICT['TEMP_WB'] = instance.upper()
desired_order = ["TITLE", "MILESTONE", "RELATED_BIOID", "NOTES"]  # Define the required order of the groups

'''
This job will convert notes and column data to a formatted text insertion into Factgrid discussion page.
This test case is for the beta bio, and will need to be mofified for other bibliographies and their custom use cases.
'''

# Define mappings for column types
MAPPINGS = {
      'TITLE': {
        'COLUMN': 'TITLE',
        'TOPIC': '=== Títulos ===',
        'EXPANDED_TITLE_U': '* Título:',
        'TITLE_Q': '** Calificador?',
        'TITLE_BD': '** Fecha inicial:',
        'TITLE_ED': '** Fecha final:',
        'TITLE_EDQ': '**?',
        'TITLE_BASIS': '** Fuente:'
    },
      'MILESTONE': {
        'COLUMN': 'MILESTONE',
        'TOPIC': '=== Hitos ===',
        'COMBINED_DETAIL': '* Evento:',
        'MILESTONE_GEOID': '',
        'MILESTONE_BD': '** Fecha inicial:',
        'MILESTONE_BDQ': '** Calificador de la fecha inicial',
        'MILESTONE_ED': '** Fecha final:',
        'MILESTONE_EDQ': '** Calificador de la fecha final',
        'MILESTONE_BASIS': '** Fuente:'
    },
      'RELATED_BIOID': {
        'COLUMN': 'RELATED_BIOID',
        'TOPIC': '=== Personas asociadas ===',
        'RELATED_BIOID': '',
        'COMBINED_BIO_DETAIL': '* Persona asociada:',
        'RELATED_BIODETAIL': '** Detalles de la persona:',
        'RELATED_BIOIDQ': '** Calificador',
        'RELATED_BIOBD': '** Fecha inicial',
        'RELATED_BIOBDQ': '** Calificador de la fecha inicial',
        'RELATED_BIOED': '** Fecha final:',
        'RELATED_BIOEDQ': '** Calificador de la fecha final',
        'RELATED_BIOBASIS': '** Fuente:'
    },
      'NOTES': {
        'COLUMN': 'NOTES',
        'TOPIC': '=== Notas ===',
        'NOTES': ''
    }
}

factgrid_url = 'https://database.factgrid.de/wiki/Item:'
first_row_path = f'first_row/{bibliography.upper()}'
bib_first_row = f"{instance.lower()}_{bibliography.upper()}_{table.upper()}_first_row_*.csv"
geo_first_row = f"{instance.lower()}_{bibliography.upper()}_GEOGRAPHY_*.csv"

def get_latest_file(base_file_name):
    file_pattern = os.path.join(first_row_path, base_file_name)
    matching_files = glob.glob(file_pattern)

    if matching_files:
        latest_file = max(matching_files, key=lambda x: x[-12:-4])  # Extract date YYYYMMDD
        print(f"Latest {base_file_name} File: {latest_file}")
        return latest_file
    else:
        print(f"No matching files found for {base_file_name}, please run the extract_first_row_from_csv.py script.")
        return None

# Get the latest first row file for the bibliography and table
bib_file = get_latest_file(bib_first_row)
geo_file = get_latest_file(geo_first_row)

# Import the CSV files
df = pd.read_csv(f"../data/processed/pre/{bibliography}/{instance}_{bibliography}_{table}.csv", low_memory=False)
df_ids = pd.read_csv(f"{bib_file}", low_memory=False)
dc_df = pd.read_csv(f"../data/clean/{bibliography}/dataclips/{bibliography}_dataclips.csv", low_memory=False)
geo_df = pd.read_csv(f"{geo_file}", low_memory=False)
lookup_df = pd.read_csv(f"../data/lookup_{instance}.csv", low_memory=False)

# Lets massage the data a bit and append the factgrid url to the QNUMBER in the QNUMBER column
lookup_df.loc[lookup_df['QNUMBER'].notnull() & (lookup_df['QNUMBER'] != ''), 'QNUMBER'] = factgrid_url + lookup_df.loc[lookup_df['QNUMBER'].notnull() & (lookup_df['QNUMBER'] != ''), 'QNUMBER'].astype(str)

# Edit TITLE_NUMBER column to prepend "BETA" to the value so it matches the mapping
columns_to_update = ['TITLE_NUMBER', 'TITLE', 'TITLE_CONNECTOR', 'RELATED_BIOCLASS']

for col in columns_to_update:
    df.loc[
        df[col].notnull() & (df[col].astype(str).str.strip() != ""),
        col
    ] = f"{bibliography.upper()} " + df.loc[
        df[col].notnull() & (df[col].astype(str).str.strip() != ""),
        col
    ]

# Create a mapping of the dataframes to use for replacing values
milestone_map = dict(zip(dc_df["code"], dc_df["es"]))
df_mapping = dict(zip(df_ids.iloc[:, 0], df_ids['EXPANDED_NAME']))
geo_mapping = dict(zip(geo_df['GEOID'], geo_df['MONIKER']))
lookup_mapping = dict(zip(lookup_df['PBID'], lookup_df['QNUMBER']))

# Combine the values from the lookup_df QNUMBER column with the df on the MILESTONE_GEOID column where the column[0] values match in both dataframes
df['GEOID_URL'] = df['MILESTONE_GEOID'].map(lookup_mapping)
df['BIODATA_URL'] = df['RELATED_BIOID'].map(lookup_mapping)

# Lets replace the values in the DataFrame with the mapping values
print(f'Replacing values in the DataFrame with the mapping values for {table} values')
# Replace mapping values in every column except the first column for source df
df.iloc[:, 1:] = df.iloc[:, 1:].replace(df_mapping)
print(f'Replacing values in the DataFrame with the mapping values for geo values')
df = df.replace(geo_mapping)
print(f'Replacing values in the DataFrame with the mapping values for dataclip values')
df = df.replace(milestone_map)
cols_to_clean = ['MILESTONE_DETAIL', 'RELATED_BIOCLASS', 'RELATED_BIOID', 'MILESTONE_GEOID']
df[cols_to_clean] = df[cols_to_clean].fillna('').astype(str) # Ensure all listed columns are strings
with open('df.csv', 'w') as file: #just for testing
    df.to_csv(file)

# Edit MILESTONE_DETAIL column to append geoid values to a combined column
df['COMBINED_DETAIL'] = df.apply(
    lambda row: row['MILESTONE_DETAIL'] + 
    (f" [{row['GEOID_URL']} {row['MILESTONE_GEOID']}]" if pd.notna(row['GEOID_URL']) and str(row['GEOID_URL']).strip() != "" and pd.notna(row['MILESTONE_GEOID']) and str(row['MILESTONE_GEOID']).strip() != "" 
     else f" [{row['GEOID_URL']}]" if pd.notna(row['GEOID_URL']) and str(row['GEOID_URL']).strip() != "" 
     else f" [{row['MILESTONE_GEOID']}]" if pd.notna(row['MILESTONE_GEOID']) and str(row['MILESTONE_GEOID']).strip() != "" 
     else ""),
    axis=1
)
# Edit RELATED_BIODETAIL column to append bioid values to a combined column
df['COMBINED_BIO_DETAIL'] = df.apply(
    lambda row: row['RELATED_BIOCLASS'] + 
    (f" [{row['BIODATA_URL']} {row['RELATED_BIOID']}]" if pd.notna(row['BIODATA_URL']) and str(row['BIODATA_URL']).strip() != "" and pd.notna(row['RELATED_BIOID']) and str(row['RELATED_BIOID']).strip() != "" 
     else f" [{row['BIODATA_URL']}]" if pd.notna(row['BIODATA_URL']) and str(row['BIODATA_URL']).strip() != "" 
     else f" [{row['RELATED_BIOID']}]" if pd.notna(row['RELATED_BIOID']) and str(row['RELATED_BIOID']).strip() != "" 
     else ""),
    axis=1
)

# Define the metadata keys that we want to skip and then arrange columns in proper order we want them read.
# Extract the first two columns from the original DataFrame to keep their order
first_two_columns = df.columns[:2].tolist()
print(first_two_columns)
desired_order = []
metadata_keys = {'COLUMN', 'TOPIC'}  # Define the metadata keys from the dict that we want to skip
# Define columns to drop from the mapping groups (if they exist) as they are not needed in the final output
drop_columns = {'MILESTONE_DETAIL', 'MILESTONE_GEOID', 'GEOID_URL', 'BIODATA_URL', 'RELATED_BIOCLASS', 'RELATED_BIOID', 'RELATED_BIOID_QNUMBER'}
for group in MAPPINGS.values():
    for col in group.keys():
        if col not in metadata_keys or col not in drop_columns:
            desired_order.append(col)
    for key in drop_columns:
        group.pop(key, None) 

# Ensure only existing columns are considered
existing_columns = [col for col in desired_order if col in df.columns]
# Add any columns that exist in the DataFrame but were not in the mapping (to keep all data)
remaining_columns = [col for col in df.columns if col not in first_two_columns + existing_columns]
# Define the final column order: MAPPINGS order first, then any remaining columns if needed
#final_column_order = first_two_columns + existing_columns + remaining_columns
final_column_order = first_two_columns + existing_columns
# Reorder DataFrame
df = df[final_column_order]

# Iterate over each mapping group and update DataFrame columns accordingly.
mapping_keys = set()
for group in MAPPINGS.values():
    for col_key, prefix in group.items():
        if col_key in metadata_keys:
            continue
        if col_key in df.columns:
            # Prepend the prefix only if the column has an existing (non-empty) value.
            df[col_key] = df[col_key].apply(
                lambda x: f"{prefix} {x}" if pd.notnull(x) and str(x).strip() != "" else x
            )
    mapping_keys.update(set(group.keys()) - metadata_keys)
#print(df.head())
first_column = df.columns[0] # PBID
second_column = df.columns[1] # QNUMBER
#columns_to_keep = [first_column] + [second_column] + ['MILESTONE_CLASS'] + [col for col in df.columns if col in mapping_keys] #just for testing
#columns_to_keep = [first_column] + [col for col in df.columns if col in mapping_keys]
columns_to_keep = [second_column] + [col for col in df.columns if col in mapping_keys]
df_milestones = df[columns_to_keep]
with open('df_milestones.csv', 'w') as file: #just for testing
    df_milestones.to_csv(file)

# Reordering function
def reorder_dict(d, order):
    return {k: d[k] for k in order if k in d}  # Keeps only keys in `order`, in specified order

def post_notes(q_number, text):
    from notes import notes
    print(f"Adding notes for {q_number} into talk page..")
    print(f"Notes: {text}")
    #notes.add_notes_to_talk_page_item(q_number, text)

def create_notes_text(aggregated):
    # Build the final text output.
    group_texts = {}
    for group_key, mapping_dict in aggregated.items():
        #lines = [str(group_key)]  # group header, e.g. the Qnumber
        lines = []
        for mapping_key, values in mapping_dict.items():
            topic = MAPPINGS.get(mapping_key, {}).get('TOPIC', "").strip()
            if topic:
                lines.append(topic)
            for val in values:
                if val.strip():  # only add non-empty values
                    lines.append(val)
        # Join lines for this group with newlines.
        #group_texts[group_key] = "\n".join(line for line in lines if line.strip() != "")
        group_texts[group_key] = "\n".join(lines) # omit group key
    return group_texts

def create_group_texts(df_milestones):
    """
    Aggregates text for each group (determined by the first column in df_milestones) following
    the order in `desired_order`. It captures all relevant columns under each mapping category.
    
    Excludes `COLUMN`, `TOPIC`, and any commented-out keys.
    """
    aggregated = {}  # key: group value (from col 0); value: dict mapping mapping_key -> list of cell values

    # Extract column names from MAPPINGS (excluding 'COLUMN' and 'TOPIC')
    mapping_columns = {}
    for key, value in MAPPINGS.items():
        mapping_columns[key] = [col for col in value.keys() if col not in ['COLUMN', 'TOPIC']]
    print(f"Mapping columns: {mapping_columns}")

    for idx, row in df_milestones.iterrows():
        group_key = row.iloc[0]  # shared group value (e.g. Qnumber [1] or pbid [0])
        if group_key not in aggregated:
            aggregated[group_key] = {}

        processed_cols = set()
        for category in desired_order:  # Process in the specified order
            if category not in mapping_columns:
                continue  # Skip if category is not in MAPPINGS

            for col in mapping_columns[category]:  # Iterate over relevant columns
                if col in processed_cols or col not in row.index:
                    continue  # Skip already processed or missing columns

                cell_value = row[col]

                # Ensure "nan" values are ignored
                value_str = str(cell_value).strip()
                if value_str.lower() == 'nan' or value_str == "":
                    continue  # Skip empty values
                # Add value to the correct category
                aggregated[group_key].setdefault(category, []).append(value_str)
                processed_cols.add(col)  # Mark column as processed
    # Reorder the dictionary
    aggregated = {bioid: reorder_dict(entries, desired_order) for bioid, entries in aggregated.items()}
    group_texts = create_notes_text(aggregated)
    return group_texts

if filetype == 'text':
    # Create text output
    group_texts = create_group_texts(df_milestones)
    with open('grouped_texts.txt', 'w') as file:
        for group_key, text in group_texts.items():
            print(f"{group_key}")
            print(f"{text}")
            post_notes(group_key, text=text)
            break
            #file.write(f"{text}\n")
    print('Text files created')
