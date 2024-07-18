import pandas as pd
import sys

# Check if the CSV file path is provided as a command line argument
if len(sys.argv) < 3:
    print("Please provide the CSV input/output file path(s) as a command line argument.")
    sys.exit(1)

# Get the CSV file path from the command line argument
csv_file_path = sys.argv[1]
csv_output_path = sys.argv[2]

# Read the data from the CSV file
data = pd.read_csv(csv_file_path)

# Find the first column name from the CSV
first_column_name = data.columns[0]
# Print the output
print("First column name:", first_column_name)

# Group the data by "MANID" column and export to csv
grouped_data = data.groupby(first_column_name).first()
grouped_data.to_csv(csv_output_path)
