import os
import pandas as pd
import csv
from datetime import datetime

from common.enums import Table
from .generic import GenericPreprocessor

class LibraryPreprocessor(GenericPreprocessor):

  TABLE = Table.LIBRARY

  def __init__(self, top_level_bib=None, qnumber_lookup_file=None) -> None:
    super().__init__(top_level_bib, qnumber_lookup_file)

  def preprocess(self):
    print(f'{datetime.now()} INFO: Processing library ..')

    file = self.get_input_csv(LibraryPreprocessor.TABLE)
    print(f'{datetime.now()} INFO: Input csv: {file}')
    df = pd.read_csv(file, dtype=str, keep_default_na=False)

    # enumerate the pb base item (id) fields
    id_fields = [
      'LIBID',
      'RELATED_GEOID',
      'RELATED_INSID',
      'RELATED_BIBID',
      'SUBJECT_BIOID',
      'SUBJECT_GEOID',
      'SUBJECT_INSID',
      'SUBJECT_SUBID'
    ]

    dataclip_fields = [
      'NAME_CLASS',
      'LIBCODE_CLASS',
      'CLASS',
      'TYPE',
      'RELATED_GEOCLASS',
      'RELATED_INSCLASS',
      'RELATED_BIBCLASS',
      'INTERNET_CLASS'
    ]

    # add new columns for the qnumbers using the lookup table if supplied
    df = self.reconcile_by_lookup(df, id_fields + dataclip_fields)

    self.write_result_csv(df, file)
    print(f'{datetime.now()} INFO: done')
