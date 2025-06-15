import sys
import csv
import re
import argparse

def normalize_string(s):
    # Remove HTML-like tags
    s_cleaned = re.sub(r'<[^>]+>', '', s).strip()

    # Case: Roman numeral + colon + number (e.g., I:346)
    match = re.match(r'^(.*?)(?:\s+([IVXLCDM]+\:\d+))$', s_cleaned)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    # Case: trailing number (e.g., DHEE 1875)
    match = re.match(r'^(.*?)(?:\s+(\d+))$', s_cleaned)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    # No split
    return s_cleaned, ''

def main():
    parser = argparse.ArgumentParser(description='Normalize string column in CSV.')
    parser.add_argument('--no-header', '-n', action='store_true',
                        help='Indicate that the input CSV has no header row.')
    args = parser.parse_args()

    reader = csv.reader(sys.stdin)
    writer = csv.writer(sys.stdout)

    first_line = True
    for row in reader:
        if not row:
            continue

        if first_line and not args.no_header:
            writer.writerow(row + ['key', 'loc'])
            first_line = False
            continue

        input_value = row[-1]
        output1, output2 = normalize_string(input_value)
        writer.writerow(row + [output1, output2])
        first_line = False

if __name__ == "__main__":
    main()
