import os
import csv
import pandas as pd
from .generic import GenericPreprocessor

UNKNOWN_LANG = 'und'
NAME_CLASS_TO_LANG = {
  'INSTITUTIONS*NAME_CLASS*L': 'la',
  'INSTITUTIONS*NAME_CLASS*E': 'en',
  'INSTITUTIONS*NAME_CLASS*S': 'es',
  'INSTITUTIONS*NAME_CLASS*P': 'pt',
  'INSTITUTIONS*NAME_CLASS*C': 'ca',
  'INSTITUTIONS*NAME_CLASS*G': 'de',
  'INSTITUTIONS*NAME_CLASS*F': 'fr',
  'INSTITUTIONS*NAME_CLASS*I': 'it',
  'INSTITUTIONS*NAME_CLASS*H': 'nld'
}

class InstitutionPreprocessor(GenericPreprocessor):
  CHARS_MAX_LEN = 400
  
  def get_name_lang(self, row):
    name_class = row['NAME_CLASS']
    if name_class:
      if name_class in NAME_CLASS_TO_LANG:
        return NAME_CLASS_TO_LANG[name_class]
      else:
        return UNKNOWN_LANG
    return ''

  def preprocess(self, file, processed_dir):
    print('INFO: Processing institutions ..')
    df_ins = pd.read_csv(file, dtype=str, keep_default_na=False)

    # Add label
    df_ins = self.add_new_column_from_value(df_ins, 'NAME_CLASS', 'INSTITUTIONS*NAME_CLASS*U', 'LABEL', 'NAME')
    self.set_column_value_by_condition(df_ins, 'LABEL.str.len()>0', 'NAME', '')

    # Name edit box
    df_ins['NAME_LANG'] = df_ins.apply (lambda row: self.get_name_lang(row), axis=1)
    df_ins = self.move_last_column_to(df_ins, self.get_column_index(df_ins, 'NAME_CLASS') + 1)

    # Milestone edit box
    self.set_column_value_by_condition(df_ins, 'MILESTONE_CLASS.str.len()==0 & (MILESTONE_DETAIL.str.len()>0 | MILESTONE_Q.str.len()>0 | MILESTONE_GEOID.str.len()>0 | MILESTONE_GEOIDQ.str.len()>0 | MILESTONE_BD.str.len()>0 | MILESTONE_BDQ.str.len()>0 | MILESTONE_ED.str.len()>0 | MILESTONE_EDQ.str.len()>0 | MILESTONE_BASIS.str.len()>0)', 'MILESTONE_CLASS', 'Type of event')
    df_ins  = self.add_new_column_by_condition(df_ins, "MILESTONE_CLASS=='INSTITUTIONS*MILESTONE_CLASS*C'", 'MILESTONE_CLASS_C', 'Noble Family', 'MILESTONE_CLASS')
    self.set_column_value_by_condition(df_ins, "MILESTONE_CLASS=='INSTITUTIONS*MILESTONE_CLASS*C'", 'MILESTONE_CLASS', '')

    # Internet edit box
    df_ins = self.add_new_column_from_value(df_ins, 'INTERNET_CLASS', 'UNIVERSAL*INTERNET_CLASS*EMA', 'INTERNET_CLASS_EMA', 'INTERNET_ADDRESS', 'mailto:{value}')
    df_ins = self.add_new_column_from_value(df_ins, 'INTERNET_CLASS', 'UNIVERSAL*INTERNET_CLASS*URL', 'INTERNET_CLASS_URL', 'INTERNET_ADDRESS')
 
    # Notes
    df_ins = self.split_str_column_by_size(df_ins, 'NOTES', self.CHARS_MAX_LEN)

    self.check_rows_empty_classes(df_ins, ['NAME_CLASS', 'INTERNET_CLASS'])

    df_ins.to_csv(os.path.join(processed_dir, os.path.basename(file)), index=False, quoting=csv.QUOTE_ALL)
    print('INFO: done.')