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

    # Split RELATED_LIBCALLNO
    df = self.split_column_by_clip(df, 'RELATED_LIBCALLNOCLASS', 'RELATED_LIBCALLNO', 'MS_ED*RELATED_LIBCALLNOCLASS',
                                   ['C', 'F', 'A', 'R', 'B', 'I', 'CIBN45', 'E'])

    # Split MILESTONE_MAKER
    df = self.split_column_by_clip(df, 'MILESTONE_CLASS', 'MILESTONE_MAKER_ID', 'MS_ED*MILESTONE_CLASS',
                                   ['P', 'W'])

    # Split MILESTONE_GEOID
    df = self.split_column_by_clip(df, 'MILESTONE_CLASS', 'MILESTONE_GEOID', 'MS_ED*MILESTONE_CLASS',
                                   ['P', 'W'])

    # Split MILESTONE_MAKER
    df = self.split_column_by_clip(df, 'MILESTONE_CLASS', 'MILESTONE_BD', 'MS_ED*MILESTONE_CLASS',
                                   ['P', 'W'])

    # Split MILESTONE_MAKER
    df = self.split_column_by_clip(df, 'MILESTONE_CLASS', 'MILESTONE_ED', 'MS_ED*MILESTONE_CLASS',
                                   ['P', 'W'])

    # Internet edit box
    df = self.split_internet_class(df)

    # enumerate the pb base item (id) fields
    id_fields = [
      'MANID',
      'MILESTONE_MAKER_ID_P',
      'MILESTONE_MAKER_ID_W',
      'MILESTONE_FUNDER_ID',
      'MILESTONE_GEOID_P',
      'MILESTONE_GEOID_W',
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
    df = self.reconcile_base_objects_by_lookup(df, id_fields)
    df = self.reconcile_dataclips_by_lookup(df, dataclip_fields)

    self.write_result_csv(df, file)
    print(f'{datetime.now()} INFO: done')
