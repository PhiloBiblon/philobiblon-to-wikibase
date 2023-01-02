import os
import pandas as pd
import csv
import random

from common.settings import DATACLIP_DIR
from .generic import GenericPreprocessor

class GeographyPreprocessor(GenericPreprocessor):
  DATACLIP_FILENAME = 'GEO_dataclips.csv'

  def __init__(self) -> None:
    super().__init__()
    self.df_dataclip = pd.read_csv(os.path.join(DATACLIP_DIR, self.DATACLIP_FILENAME), dtype=str, keep_default_na=False)
    self.runid = random.randint(0,999999)

  def make_desc(self, row):
    if row['NAME'] != row['MONIKER']:
      return row['MONIKER']
    return ""

  def decorate_with_runid(self, s):
    if len(s) == 0:
      return s
    return f'{self.runid} {s}'

  def quote_string(self, s):
    return f'"{s}"'

  def preprocess(self, file, processed_dir):
    print('INFO: Processing geography ..')
    df = pd.read_csv(file, dtype=str, keep_default_na=False)

    # Get the en and es for TYPE
    df = self.add_new_column_from_mapping(df, 'TYPE', self.df_dataclip, 'code', 'es', 'TYPE_es')
    df = self.move_last_column_after(df, 'TYPE')
    df = self.add_new_column_from_mapping(df, 'TYPE', self.df_dataclip, 'code', 'en', 'TYPE_en')
    df = self.move_last_column_after(df, 'TYPE_es')

    # Create columns for direct consumption by quickstatements csv
    df['Len'] = df.apply (lambda row: self.decorate_with_runid(row["NAME"]), axis=1)
    df['Den'] = df.apply (lambda row: self.decorate_with_runid(self.make_desc(row)), axis=1)
    df['Aen'] = df.apply (lambda row: self.decorate_with_runid(row["GEOID"]), axis=1)
    df['P-PBID'] = df.apply (lambda row: self.quote_string(row["GEOID"]), axis=1)

    df.to_csv(os.path.join(processed_dir, os.path.basename(file)), index=False, quoting=csv.QUOTE_ALL)
    print('INFO: done.')
