import os
import pandas as pd

INPUT_DIR='../../data/clean/BETA'

filenames = next(os.walk(INPUT_DIR), (None, None, []))[2]

long_notes = 0
total_notes = 0
for file in filenames:
  df = pd.read_csv(os.path.join(INPUT_DIR, file), dtype=str)
  for _, row in df.iterrows():
    if not pd.isnull(row['NOTES']):
      total_notes += 1
      notes_len = len(row['NOTES'])
      if notes_len > 400:
        long_notes += 1
        print(f'{row[0]} : {notes_len}')

print(f'{long_notes} / {total_notes} are too much longer ')