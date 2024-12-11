import pandas as pd
import argparse
from fuzzywuzzy import fuzz
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('--bib', type=str, default="BITECA", help="BIB to compare join with BETA", choices=['BITECA', 'BITAGAP'])
parser.add_argument("--table", help="Table to process", choices=['analytic', 'biography', 'geography', 'institutions', 'library', 'subject', 'bibliography', 'copies', 'ms_ed', 'uniform_title'], required=True)
parser.add_argument('--instance', default='PBCOG', choices=['PBCOG', 'FACTGRID'], help='Specify an instance from the list.  Default is PBCOG.')
parser.add_argument('--fuzzy', action='store_true', help="Use fuzzy matching to merge the two files")
parser.add_argument('--column', type=str, help="Column to use for matching")
parser.add_argument('--column2', type=str, help="Second column to use for matching")  # Optional
args = parser.parse_args()

output_file = f'matched_{args.bib.lower()}_{args.instance.lower()}_{args.table}_'

# Define the fuzzy merge function
def fuzzy_merge(df1, df2, on_columns):
    def fuzzy_match(row):
        best_match = None
        best_similarity = 0  # Adjust the threshold if needed
        for index, row2 in df2.iterrows():
            similarity = fuzz.ratio(row[on_columns[0]], row2[on_columns[0]])
            if similarity >= 80:  # Adjust the threshold if needed
                best_match = row2
                print(f'Match found: {row[on_columns[0]]} and {row2[on_columns[0]]} with similarity {similarity}')
                break

        if best_match is not None:
            # Assuming you want to match on the supplied column
            return best_match[on_columns]
        else:
            return np.nan
    df1['matched_row'] = df1.apply(fuzzy_match, axis=1)
    df1 = df1.dropna(subset=['matched_row'])
    # Concatenate the matched rows from df1 with the corresponding rows from df2
    matched_indices = df1['matched_row'].apply(lambda x: x.name if isinstance(x, pd.Series) else np.nan).dropna().astype(int)
    matched_df2 = df2.loc[matched_indices]
    merged_df = pd.concat([df1.reset_index(drop=True), matched_df2.reset_index(drop=True)], axis=1)
    #merged_df = pd.concat([df1, df2.loc[df1['matched_row'].index]], axis=1)
    return merged_df.drop('matched_row', axis=1)

# Read the two CSV files
df1 = pd.read_csv(f'../data/processed/pre/BETA/{args.instance.lower()}_beta_{args.table}.csv', low_memory=False)
df2 = pd.read_csv(f'../data/processed/pre/{args.bib}/{args.instance.lower()}_{args.bib.lower()}_{args.table}.csv', low_memory=False)
# Setting columns and dropping rows with missing values
column_list = [args.column]
if args.column2:
    column_list.append(args.column2)
print(f"Columns to check for missing values: {column_list}")
df1 = df1.dropna(subset=column_list)
df2 = df2.dropna(subset=column_list)
#df1 = df1.set_index(args.column)
#df2 = df2.set_index(args.column)

# Perform the fuzzy merge if specified
print("Performing merge on column:", args.column)
if args.fuzzy:
    print("Performing fuzzy merge on column:", column_list)
    merged_df = fuzzy_merge(df1, df2, on_columns=column_list)
    output_file += 'fuzzy'
else:
    print("Performing merge on column:", column_list)
    #merged_df = df1.merge(df2, how='outer', left_index=True, right_index=True)
    merged_df = df1.merge(df2, how='inner', on=column_list)

# Save the merged DataFrame to a new CSV file
merged_df.to_csv(f'{output_file}.csv', index=False)

