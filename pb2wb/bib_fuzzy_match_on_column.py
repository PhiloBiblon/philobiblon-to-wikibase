import pandas as pd
import argparse
from fuzzywuzzy import fuzz

parser = argparse.ArgumentParser()
parser.add_argument('--bib', type=str, default="BITECA", help="BIB to compare join with BETA", choices=['BITECA', 'BITAGAP'])
parser.add_argument("--table", help="Table to process", choices=['analytic', 'biography', 'geography', 'institutions', 'library', 'subject', 'bibliography', 'copies', 'ms_ed', 'uniform_title'], required=True)
parser.add_argument('--instance', default='PBCOG', choices=['PBCOG', 'FACTGRID'], help='Specify an instance from the list.  Default is PBCOG.')
parser.add_argument('--fuzzy', action='store_true', help="Use fuzzy matching to merge the two files")
parser.add_argument('--column', type=str, help="Column to use for matching")
args = parser.parse_args()

output_file = f'matched_{args.bib.lower()}_{args.instance.lower()}_{args.table}'
combined_df = pd.DataFrame()

# Function to combine dictionaries on merged fuzzy rows with duplicate keys
def combine_dicts(merged_list):
  combined_dict = {}
  for dict in merged_list:
    for key, value in dict.items():
      if key in combined_dict:
        # If the key already exists, append bib to it to make it unique
        i = args.bib
        new_key = f"{key}_{i}"
        while new_key in combined_dict:
          i += args.bib
          new_key = f"{key}_{i}"
        combined_dict[new_key] = value
      else:
        combined_dict[key] = value
  return combined_dict

# fuzzy merge function
def fuzzy_merge(df1, df2, on_columns, threshold=90):
    matched_rows = []
    # Function to perform fuzzy matching
    def fuzzy_match(row):
        for index, row2 in df2.iterrows():
            similarity = fuzz.ratio(row[on_columns[0]], row2[on_columns[0]])
            if similarity >= threshold:
                print(f'Match found: {row[on_columns[0]]} and {row2[on_columns[0]]} with similarity {similarity}')
                merged_list = [row, row2]
                # Combine the two dictionaries and modify the key if there are duplicates
                combined_dict = combine_dicts(merged_list)
                # Convert the dictionary to a DataFrame
                temp_df = pd.DataFrame([combined_dict])
                matched_rows.append(temp_df)

    df1.apply(fuzzy_match, axis=1)
    merged_df = pd.concat(matched_rows, ignore_index=True)
    return merged_df

# Read the two CSV files
beta_csv = f'../data/processed/pre/BETA/{args.instance.lower()}_beta_{args.table}.csv'
alt_csv = f'../data/processed/pre/{args.bib}/{args.instance.lower()}_{args.bib.lower()}_{args.table}.csv'
print(f"Reading files: {beta_csv} and {alt_csv}")
df1 = pd.read_csv(beta_csv, low_memory=False)
df2 = pd.read_csv(alt_csv, low_memory=False)
# Setting columns and dropping rows with missing values
column_list = [args.column]
print(f"Columns to check for missing values: {column_list}")
# Drop rows with missing values in the specified columns
df1 = df1.dropna(subset=column_list)
df2 = df2.dropna(subset=column_list)
# Select only the deired columns to merge
df1 = df1.loc[:, [df1.columns[0], *column_list]]
df2 = df2.loc[:, [df2.columns[0], *column_list]]
# Drop duplicates in the specified columns
df1 = df1.drop_duplicates(subset=column_list, keep='first')  # Keep the first occurrence of the duplicate
df2 = df2.drop_duplicates(subset=column_list, keep='first')

# Perform the fuzzy merge if specified
if args.fuzzy:
    print("Performing fuzzy merge on column:", column_list)
    merged_df = fuzzy_merge(df1, df2, on_columns=column_list)
    output_file += '_fuzzy'
else:
    print("Performing merge on column:", column_list)
    merged_df = df1.merge(df2, how='inner', on=column_list)

# Drop any accidental duplicates and save the merged DataFrame to a new CSV file
merged_df.drop_duplicates(subset=merged_df.columns[0], inplace=True)
merged_df.to_csv(f'{output_file}.csv', index=False)
