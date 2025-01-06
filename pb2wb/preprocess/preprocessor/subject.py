import os
import pandas as pd
import csv
from datetime import datetime

from common.enums import Table
from common.data_dictionary import DATADICT
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
   
  def __init__(self, top_level_bib=None, qnumber_lookup_file=None, instance=None) -> None:
    super().__init__(top_level_bib, qnumber_lookup_file, instance)

  def get_name_lang(self, row):
    name_class = row['HV_CLASS']
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

    df = self.process_defaults_for_editbox(df, SubjectPreprocessor.TABLE.value, 'variant_headings')

    # Internet edit box
    df = self.split_internet_class(df)

    # add new columns for the qnumbers using the lookup table if supplied
    df = self.add_qnumber_columns(df, SubjectPreprocessor.TABLE)

    # adding the name_lang column
    df['NAME_LANG'] = df.apply (lambda row: self.get_name_lang(row), axis=1)

    df = self.move_last_column_after(df, 'HV_CLASS')

    # truncate any fields that are too long
    df = self.truncate_dataframe(df)

    self.write_result_csv(df, file)
    print(f'{datetime.now()} INFO: done')
