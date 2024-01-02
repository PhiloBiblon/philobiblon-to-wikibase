import os
import pandas as pd
import csv
from datetime import datetime

from common.enums import Table
from .generic import GenericPreprocessor

class SubjectPreprocessor(GenericPreprocessor):
  TABLE = Table.SUBJECT

  def __init__(self, top_level_bib=None, qnumber_lookup_file=None) -> None:
    super().__init__(top_level_bib, qnumber_lookup_file)

  def preprocess(self):
    print(f'{datetime.now()} INFO: Processing subject ..')

    file = self.get_input_csv(SubjectPreprocessor.TABLE)
    print(f'{datetime.now()} INFO: Input csv: {file}')
    df = pd.read_csv(file, dtype=str, keep_default_na=False)

    # Internet edit box
    df = self.split_internet_class(df)

    # enumerate the pb base item (id) fields
    id_fields = [
      'SUBID',
      'HB_SUBID',
      'HR_SUBID',
      'RELATED_BIBID',
      'RELATED_MANID'
    ]

    dataclip_fields = [
      'HEADING_MAIN',
      'HEADING_VARIANT',
      'HM_CLASS',
      'HM_TYPE',
      'HV_CLASS',
      'HV_TYPE',
      'RELATED_BIBCLASS',
      'RELATED_MANCLASS',
      'INTERNET_CLASS'
    ]

    # add new columns for the qnumbers using the lookup table if supplied
    df = self.reconcile_by_lookup(df, id_fields + dataclip_fields)

    self.write_result_csv(df, file)
    print(f'{datetime.now()} INFO: done')
