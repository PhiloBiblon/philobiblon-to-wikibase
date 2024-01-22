import os
import pandas as pd
import csv
from datetime import datetime

from common.enums import Table
from .generic import GenericPreprocessor

class GeographyPreprocessor(GenericPreprocessor):
  TABLE = Table.GEOGRAPHY

  def __init__(self, top_level_bib=None, qnumber_lookup_file=None) -> None:
    super().__init__(top_level_bib, qnumber_lookup_file)

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

    # enumerate the pb base item (id) fields
    id_fields = [
      'GEOID', 'RELATED_GEOID_S', 'RELATED_GEOID_P', 'RELATED_BIBID', 'RELATED_MANID',
      'SUBJECT_BIOID', 'SUBJECT_INSID', 'SUBJECT_SUBID'
    ]
    dataclip_fields = [
      'NAME_CLASS', 'CLASS', 'TYPE', 'RELATED_GEOCLASS', 'RELATED_BIBCLASS', 'RELATED_MANCLASS', 'INTERNET_CLASS'
    ]

    # add new columns for the qnumbers using the lookup table if supplied
    df = self.reconcile_by_lookup(df, id_fields + dataclip_fields)

    self.write_result_csv(df, file)
    print(f'{datetime.now()} INFO: done')
