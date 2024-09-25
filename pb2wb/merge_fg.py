import pandas as pd

# Read the first CSV file
df1 = pd.read_csv('fg_476.csv')

# Read the second CSV file
df2 = pd.read_csv('fg_lang.csv')

# Perform the join operation based on the "pbid" column
merged_df = pd.merge(df1, df2, left_on='pbid', right_on='alias').drop_duplicates()
merged_df['item'] = merged_df['item_x']
merged_df['itemLabel'] = merged_df['itemLabel_x']
merged_df['item_y'] = merged_df['item_y']
merged_df['itemLabel_y'] = merged_df['itemLabel_y']
merged_df = merged_df.drop(['item_x', 'itemLabel_x', 'item_y', 'itemLabel_y', 'alias'], axis=1)

# Print the merged dataframe
print(merged_df)

# Export the merged dataframe to a CSV file
merged_df.to_csv('merged_data.csv', index=False)

# Find items from df1 pbid that do not match in df2 alias
unmatched_items = df1[~df1['pbid'].isin(df2['alias'])]

# Print the unmatched items
print(unmatched_items)

unmatched_items_vv = df2[~df2['alias'].isin(df1['pbid'])]

# Print the unmatched items
unmatched_items_vv = unmatched_items_vv.rename(columns={'alias': 'pbid'})

combined_unmatched_items = pd.concat([unmatched_items, unmatched_items_vv])

# Export the merged dataframe to a CSV file
combined_unmatched_items.to_csv('merged_missing_data.csv', index=False)