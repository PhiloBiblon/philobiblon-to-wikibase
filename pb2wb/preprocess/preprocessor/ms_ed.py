import os
import pandas as pd
import csv
from datetime import datetime

from common.enums import Table
from .generic import GenericPreprocessor

class MsEdPreprocessor(GenericPreprocessor):
  TABLE = Table.MS_ED

  def __init__(self, top_level_bib=None, qnumber_lookup_file=None) -> None:
    super().__init__(top_level_bib, qnumber_lookup_file)

  def preprocess(self):
    print(f'{datetime.now()} INFO: Processing ms_ed ..')

    file = self.get_input_csv(MsEdPreprocessor.TABLE)
    print(f'{datetime.now()} INFO: Input csv: {file}')
    df = pd.read_csv(file, dtype=str, keep_default_na=False)
    clazz = ['C', 'F', 'A', 'R', 'B', 'I', 'CIBN45', 'E']

    for c in clazz:
        value = 'MS_ED*RELATED_LIBCALLNOCLASS*' + c
        new_col_name = 'RELATED_CALLNO_' + c
        df[new_col_name] = (df['RELATED_LIBCALLNOCLASS'] == value) * 1 * df['RELATED_LIBCALLNO']
        df = self.move_last_column_after(df, 'RELATED_LIBCALLNO')

    # Internet edit box
    df = self.split_internet_class(df)

    # enumerate the pb base item (id) fields
    id_fields = [
      'MANID',
      'MILESTONE_MAKER_ID',
      'MILESTONE_FUNDER_ID',
      'MILESTONE_GEOID',
      'OWNER_ID',
      'OWNER_GEOID',
      'FIRST_ANAID',
      'FIRST_TEXID',
      'RELATED_BIOID',
      'RELATED_LIBID',
      'RELATED_LIBEVENTGEOID',
      'RELATED_BIBID',
      'RELATED_MANID',
      'RELATED_UNIID',
      'SUBJECT_BIOID',
      'SUBJECT_GEOID',
      'SUBJECT_INSID',
      'SUBJECT_SUBID'
    ]

    dataclip_fields = [
      'STATUS',
      'MATERIAL',
      'FORMAT',
      'LEAF_CLASS',
      'SIZE_CLASS',
      'PAGE_CLASS',
      'HAND_CLASS',
      'FONT_CLASS',
      'WATERMARK_CLASS',
      'GRAPHIC_CLASS',
      'MUSIC_CLASS',
      'FEATURE_CLASS',
      'MILESTONE_CLASS',
      'CLASS',
      'RELATED_BIOCLASS',
      'RELATED_LIBCALLNOCLASS',
      'RELATED_LIBEVENTCLASS',
      'RELATED_BIBCLASS',
      'RELATED_MANCLASS',
      'RELATED_UNICLASS',
      'INTERNET_CLASS'
    ]

    # add new columns for the qnumbers using the lookup table if supplied
    df = self.reconcile_by_lookup(df, id_fields + dataclip_fields)

    self.write_result_csv(df, file)
    print(f'{datetime.now()} INFO: done')
