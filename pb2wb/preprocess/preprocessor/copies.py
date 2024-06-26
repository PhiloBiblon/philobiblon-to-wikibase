import os
import pandas as pd
import csv
from datetime import datetime

from common.enums import Table
from .generic import GenericPreprocessor

class CopiesPreprocessor(GenericPreprocessor):
  TABLE = Table.COPIES

  def __init__(self, top_level_bib=None, qnumber_lookup_file=None) -> None:
    super().__init__(top_level_bib, qnumber_lookup_file)

  def preprocess(self):
    print(f'{datetime.now()} INFO: Processing copies ..')

    file = self.get_input_csv(CopiesPreprocessor.TABLE)
    print(f'{datetime.now()} INFO: Input csv: {file}')
    df = pd.read_csv(file, dtype=str, keep_default_na=False)

    # Split RELATED_LIBCALLNO
    df = self.split_column_by_clip(df, 'RELATED_LIBCALLNOCLASS', 'RELATED_LIBCALLNO', 'MS_ED*RELATED_LIBCALLNOCLASS',
                                   ['C', 'F', 'A', 'R', 'B', 'I', 'CIBN45', 'E'])

    # Internet edit box
    df = self.split_internet_class(df)

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
      'STATUS',
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

    # add new columns for the qnumbers using the lookup table if supplied
    df = self.reconcile_base_objects_by_lookup(df, id_fields)
    df = self.reconcile_dataclips_by_lookup(df, dataclip_fields)

    self.write_result_csv(df, file)
    print(f'{datetime.now()} INFO: done')
