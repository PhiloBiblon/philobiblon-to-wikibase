import os
import pandas as pd
import csv
from datetime import datetime

from common.enums import Table
from common.data_dictionary import DATADICT
from .generic import GenericPreprocessor

class GeographyPreprocessor(GenericPreprocessor):
  DATACLIP_FILENAME = 'beta_dataclips.csv'
  TABLE = Table.GEOGRAPHY
  UNKNOWN_LANG = 'und'
  NAME_CLASS_TO_LANG = {
    'GEOGRAPHY*NAME_CLASS*C': 'ca',
    'GEOGRAPHY*NAME_CLASS*E': 'en',
    'GEOGRAPHY*NAME_CLASS*F': 'fr',
    'GEOGRAPHY*NAME_CLASS*G': 'de',
    'GEOGRAPHY*NAME_CLASS*I': 'it',
    'GEOGRAPHY*NAME_CLASS*L': 'la',
    'GEOGRAPHY*NAME_CLASS*O': 'es',
    'GEOGRAPHY*NAME_CLASS*P': 'pt',
    'GEOGRAPHY*NAME_CLASS*Q': 'es',
    'GEOGRAPHY*NAME_CLASS*S': 'es',
    'GEOGRAPHY*NAME_CLASS*U': 'es',
    'GEOGRAPHY*NAME_CLASS*V': 'eu',
    'GEOGRAPHY*NAME_CLASS*GA': 'gl',
    'GEOGRAPHY*NAME_CLASS*A': 'ar'
 }

  def __init__(self, top_level_bib=None, qnumber_lookup_file=None, instance=None) -> None:
    super().__init__(top_level_bib, qnumber_lookup_file, instance)

  def get_name_lang(self, row):
    name_class = row['NAME_CLASS']
    if name_class:
      if name_class in self.NAME_CLASS_TO_LANG:
        return self.NAME_CLASS_TO_LANG[name_class]
      else:
        return self.UNKNOWN_LANG
    return ''

  def make_desc(self, row):
    if row['NAME'] != row['MONIKER']:
      return row['MONIKER']
    return ""

  def preprocess(self):
    print(f'{datetime.now()} INFO: Processing geography ..')

    file = self.get_input_csv(GeographyPreprocessor.TABLE)
    print(f'{datetime.now()} INFO: Input csv: {file}')
    df = pd.read_csv(file, dtype=str, keep_default_na=False)

    # Internet edit box
    df = self.split_internet_class(df)

    # Split RELATED_GEOID
    df = self.split_column_by_clip(df, 'RELATED_GEOCLASS', 'RELATED_GEOID', 'GEOGRAPHY*RELATED_GEOCLASS',
                                   ['P', 'S'])

    # add new columns for the qnumbers using the lookup table if supplied
    df = self.add_qnumber_columns(df, GeographyPreprocessor.TABLE)

    # adding the name_lang column
    df['NAME_LANG'] = df.apply (lambda row: self.get_name_lang(row), axis=1)

    df = self.move_last_column_after(df, 'NAME_CLASS')

    self.write_result_csv(df, file)
    print(f'{datetime.now()} INFO: done')
