import pandas as pd

# Read the CSV files into a DataFrames
df = pd.read_csv('p476_fg_0903.csv')
df2 = pd.read_csv('reconcile_list_0903.csv')
df3 = pd.read_csv('fg_places_300k.csv')

# Remove rows from df1 that match id's in df2
df2 = df2[~df2['alias'].isin(df['philoBiblonID'])]
#df2 = df[df['philoBiblonID'].isin(df2['alias'])]
df2 = df2.sort_values('alias')
df2.to_csv('geo_reconcile_0903.csv', index=False)

# Clean the 'INTERNET_ADDRESS' and 'Wikidata Qid' columns from the dataframes
#df2['INTERNET_ADDRESS'] = df2['INTERNET_ADDRESS'].str.extract(r'/(Q\w+)$')
#df3['Wikidata link'] = df3['Wikidata link'].str.extract(r'/(Q\w+)$')

# Print the updated DataFrames
#print(df2)
#print(df3)

# Merge the two DataFrames on the 'INTERNET_ADDRESS' and 'Wikidata Qid' columns and print the result
#merged_df = pd.merge(df2, df3, left_on='INTERNET_ADDRESS', right_on='Wikidata link', how='inner')
#print(merged_df)

# Export the merged DataFrame to a new CSV file
#merged_df.to_csv('geo_reconciled.csv', index=False)
