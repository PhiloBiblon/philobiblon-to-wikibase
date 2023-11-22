import os
import pandas as pd
import csv
from datetime import datetime

from common.settings import DATACLIP_DIR
from .generic import GenericPreprocessor

class BibliographyPreprocessor(GenericPreprocessor):
  DATACLIP_FILENAME = 'beta_dataclips.csv'

  def __init__(self) -> None:
    super().__init__()
    self.df_dataclip = pd.read_csv(os.path.join(DATACLIP_DIR, self.DATACLIP_FILENAME), dtype=str, keep_default_na=False)

  def preprocess(self, file, processed_dir, qnumber_lookup_file):
    print(f'{datetime.now()} INFO: Processing bibliography ..')

    df = pd.read_csv(file, dtype=str, keep_default_na=False)

    
    df['CREATOR_FULLNAME'] = df['CREATOR_FNAME'] + ' ' + df['CREATOR_LNAME']
    df = self.move_last_column_after(df, 'CREATOR_LNAME')
      
    df['ADJUNCT_FULLNAME'] = df['ADJUNCT_FNAME'] + ' ' + df['ADJUNCT_LNAME']
    df = self.move_last_column_after(df, 'ADJUNCT_LNAME')

    # the following None initialization is temporary (set for testing)
    lookup_df = None
      
    # lookup_df = pd.read_csv(qnumber_lookup_file, dtype=str, keep_default_na=False)

    # enumerate the pb base item (id) fields
    id_fields = [
      'BIBID',
      'RELATED_LIBID',
      'RELATED_BIBID',
      'SUBJECT_BIOID',
      'SUBJECT_GEOID',
      'SUBJECT_INSID',
      'SUBJECT_SUBID'
    ]

    dataclip_fields = [
      'CREATOR_ROLE',
      'ADJUNCT_ROLE',
      'LOCATION_CLASS',
      'ID_CLASS',
      'FORM',
      'TYPE',
      'MEDIUM',
      'CLASS',
      'RELATED_BIBCLASS',
      'INTERNET_CLASS'
    ]

    if lookup_df is not None:
      for field in id_fields + dataclip_fields:
        df = self.add_new_column_from_mapping(df, field, lookup_df, 'PBID', 'QNUMBER', field + '_QNUMBER')
        df = self.move_last_column_after(df, field)

    df.to_csv(os.path.join(processed_dir, os.path.basename(file)), index=False, quoting=csv.QUOTE_ALL)
    print(f'{datetime.now()} INFO: done')
