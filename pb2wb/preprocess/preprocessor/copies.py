import os
import pandas as pd
import csv
from datetime import datetime

from common.settings import DATACLIP_DIR
from .generic import GenericPreprocessor

class CopiesPreprocessor(GenericPreprocessor):
  DATACLIP_FILENAME = 'beta_dataclips.csv'

  def __init__(self) -> None:
    super().__init__()
    self.df_dataclip = pd.read_csv(os.path.join(DATACLIP_DIR, self.DATACLIP_FILENAME), dtype=str, keep_default_na=False)

  def preprocess(self, file, processed_dir, qnumber_lookup_file):
    print(f'{datetime.now()} INFO: Processing copies ..')

    df = pd.read_csv(file, dtype=str, keep_default_na=False)
    clazz = ['C', 'F', 'A', 'R', 'B', 'I', 'CIBN45', 'E']

    for c in clazz:
        value = 'MS_ED*RELATED_LIBCALLNOCLASS*' + c
        new_col_name = 'RELATED_CALLNO_' + c
        df[new_col_name] = (df['RELATED_LIBCALLNOCLASS'] == value) * 1 * df['RELATED_LIBCALLNO']    
        df = self.move_last_column_after(df, 'RELATED_LIBCALLNO')

    lookup_df = None
    #lookup_df = pd.read_csv(qnumber_lookup_file, dtype=str, keep_default_na=False)

    # enumerate the pb base item (id) fields
    id_fields = [
      'COPID',
      'TEXT_MANID',
      'OWNER_ID',
      'OWNER_GEOID',
      'RELATED_BIOID',
      'RELATED_LIBID',
      'RELATED_LIBEVENTGEOID',
      'RELATED_BIBID',
      'RELATED_MANID',
      'RELATED_COPID',
      'SUBJECT_BIOID',
      'SUBJECT_GEOID',
      'SUBJECT_INSID',
      'SUBJECT_SUBID'
    ]
    dataclip_fields = [
      'MATERIAL',
      'FORMAT',
      'LEAF_CLASS',
      'SIZE_CLASS',
      'PAGE_CLASS',
      'FONT_CLASS',
      'WATERMARK_CLASS',
      'GRAPHIC_CLASS',
      'MUSIC_CLASS',
      'FEATURE_CLASS',
      'RELATED_BIOCLASS',
      'RELATED_LIBCALLNOCLASS',
      'RELATED_LIBEVENTCLASS',
      'RELATED_BIBCLASS',
      'RELATED_MANCLASS',
      'RELATED_COPCLASS',
      'INTERNET_CLASS'
    ]

    if lookup_df is not None:
      for field in id_fields + dataclip_fields:
        df = self.add_new_column_from_mapping(df, field, lookup_df, 'PBID', 'QNUMBER', field + '_QNUMBER')
        df = self.move_last_column_after(df, field)

    df.to_csv(os.path.join(processed_dir, os.path.basename(file)), index=False, quoting=csv.QUOTE_ALL)
    print(f'{datetime.now()} INFO: done')
