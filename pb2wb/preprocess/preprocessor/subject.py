import os
import pandas as pd
import csv
from datetime import datetime

from common.settings import DATACLIP_DIR
from .generic import GenericPreprocessor

class SubjectPreprocessor(GenericPreprocessor):
  DATACLIP_FILENAME = 'beta_dataclips.csv'

  def __init__(self) -> None:
    super().__init__()
    self.df_dataclip = pd.read_csv(os.path.join(DATACLIP_DIR, self.DATACLIP_FILENAME), dtype=str, keep_default_na=False)

  def preprocess(self, file, processed_dir, qnumber_lookup_file):
    print(f'{datetime.now()} INFO: Processing subject ..')

    df = pd.read_csv(file, dtype=str, keep_default_na=False)
    lookup_df = pd.read_csv(qnumber_lookup_file, dtype=str, keep_default_na=False)

    # enumerate the pb base item (id) fields
    id_fields = [
      'SUBID',
      'HB_SUBID',
      'HR_SUBID',
      'RELATED_BIBID',
      'RELATED_MANID'
    ]

    dataclip_fields = [
      'HM_CLASS',
      'HM_TYPE',
      'HV_CLASS',
      'HV_TYPE',
      'RELATED_BIBCLASS',
      'RELATED_MANCLASS',
      'INTERNET_CLASS'
    ]

    if lookup_df is not None:
      for field in id_fields + dataclip_fields:
        df = self.add_new_column_from_mapping(df, field, lookup_df, 'PBID', 'QNUMBER', field + '_QNUMBER')
        df = self.move_last_column_after(df, field)

    df.to_csv(os.path.join(processed_dir, os.path.basename(file)), index=False, quoting=csv.QUOTE_ALL)
    print(f'{datetime.now()} INFO: done')
