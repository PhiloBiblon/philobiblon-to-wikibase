import os
import pandas as pd
import csv
from datetime import datetime

from common.enums import Table
from .generic import GenericPreprocessor

class SubjectPreprocessor(GenericPreprocessor):
  DATACLIP_FILENAME = 'beta_dataclips.csv'
  TABLE = Table.SUBJECT
  UNKNOWN_LANG = 'und'
  NAME_CLASS_TO_LANG = {
    'SUBJECT*HV_CLASS*CAT':	    'ca',
    'SUBJECT*HV_CLASS*ENGLISH':	'en',
    'SUBJECT*HV_CLASS*FRENCH':	'fr',
    'SUBJECT*HV_CLASS*G':		'de',
    'SUBJECT*HV_CLASS*I':		'it',
    'SUBJECT*HV_CLASS*LATIN':	'la',
    'SUBJECT*HV_CLASS*P':		'pt',
    'SUBJECT*HV_CLASS*SPANISH':	'es'
  }
   
  def __init__(self, top_level_bib=None, qnumber_lookup_file=None) -> None:
    super().__init__(top_level_bib, qnumber_lookup_file)

  def get_name_lang(self, row):
    name_class = row['NAME_CLASS']
    if name_class:
      if name_class in self.NAME_CLASS_TO_LANG:
        return self.NAME_CLASS_TO_LANG[name_class]
      else:
        return self.UNKNOWN_LANG
    return ''

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

    # adding the name_lang column
    df['NAME_LANG'] = df.apply (lambda row: self.get_name_lang(row), axis=1)
  
    self.write_result_csv(df, file)
    print(f'{datetime.now()} INFO: done')
