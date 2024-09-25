# Table to be split
table = 'geography'

# Read the original quickstatements file
with open(f'../data/processed/post/BETA/beta_{table}.qs', 'r') as file:
    original_lines = file.readlines()

def find_unique_items(unique_items, update_file):
    # Find all other rows that start with the same 'Q' item
    updated_lines = []
    for line in original_lines:
        if line.startswith('Q'):
            item = line.split('\t')[0]
            if item in unique_items:
                updated_lines.append(line)

            # Replace tabs with "|"
            #updated_lines = [line.replace('\t', '|') for line in updated_lines]

            # Replace newlines with "||"
            #updated_lines = ['||'.join(line.splitlines()) for line in updated_lines]

    # Write the updated quickstatements file
    with open(update_file, 'w') as file:
        file.writelines(updated_lines)

# Find the first 250 unique items where the rows start with 'Q'
unique_items = set()
file_number = 0
last_item = None

for line in original_lines:
    update_file = f'split_{table}_qs' + "_" + str(file_number) + ".qs"
    if line.startswith('Q'):
        item = line.split('\t')[0]
        unique_items.add(item)
        if len(unique_items) == 250:
            # Check for duplication after adding the first item
            if last_item in unique_items:
                print(f'Last item {last_item} is in the set')
                unique_items.remove(last_item)

            find_unique_items(unique_items, update_file)
            file_number += 1

            # Set last_item after clearing the previous set
            unique_items.clear()
            last_item = item
        else:
            continue
