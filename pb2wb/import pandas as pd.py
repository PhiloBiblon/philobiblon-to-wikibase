import pandas as pd

# Read the CSV file
df = pd.read_csv('BETA_unreconciled_geo.csv')
df2 = pd.read_csv('../data/clean/BETA/csvs/beta_geography.csv')

# Inner join df and df2 on column GEOID
#merged_df = df2.merge(df, left_on='GEOID', right_on=df.columns[1], how='inner')
#merged_df = df.merge(df2, left_on=df.columns[1], right_on='GEOID', how='right')

# Create a new dataframe where column 1 of df is in df2
#new_df = df[df[df.columns[1]].isin(df2['GEOID'])]
new_df = df2[df2['GEOID'].isin(df[df.columns[1]])]
print(new_df[new_df['MONIKER'].str.contains(r'\(.*\)', na=False, regex=True)])

# Remove duplicate rows
#new_df = new_df.drop_duplicates()

# Print the result
#print(new_df)
#new_df.to_csv('merged_unreconciled_geo.csv', index=False)

# Remove strings wrapped in () if present in MONIKER
#new_df['MONIKER'] = new_df['MONIKER'].str.replace(r'\(.*\)', '', regex=True)
#print(new_df)

