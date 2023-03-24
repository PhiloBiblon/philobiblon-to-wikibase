from glob import escape
import os
import csv
import pandas as pd
from datetime import datetime

from common.settings import DATACLIP_DIR
from .generic import GenericPreprocessor

class InstitutionPreprocessor(GenericPreprocessor):
  CHARS_MAX_LEN = 400
  UNKNOWN_LANG = 'und'
  NAME_CLASS_TO_LANG = {
    'INSTITUTIONS*NAME_CLASS*L': 'la',
    'INSTITUTIONS*NAME_CLASS*E': 'en',
    'INSTITUTIONS*NAME_CLASS*S': 'es',
    'INSTITUTIONS*NAME_CLASS*O': 'es',
    'INSTITUTIONS*NAME_CLASS*P': 'pt',
    'INSTITUTIONS*NAME_CLASS*C': 'ca',
    'INSTITUTIONS*NAME_CLASS*G': 'de',
    'INSTITUTIONS*NAME_CLASS*F': 'fr',
    'INSTITUTIONS*NAME_CLASS*I': 'it',
    'INSTITUTIONS*NAME_CLASS*H': 'nl',
    'INSTITUTIONS*NAME_CLASS*U': 'es'
  }
  DATACLIP_FILENAME = 'beta_dataclips.csv'

  def __init__(self) -> None:
    super().__init__()
    self.df_dataclip = pd.read_csv(os.path.join(DATACLIP_DIR, self.DATACLIP_FILENAME), dtype=str, keep_default_na=False)
  
  def get_name_lang(self, row):
    name_class = row['NAME_CLASS']
    if name_class:
      if name_class in self.NAME_CLASS_TO_LANG:
        return self.NAME_CLASS_TO_LANG[name_class]
      else:
        return self.UNKNOWN_LANG
    return ''

  def lookupDictionary(self, code, lang):    
    cell_value = self.df_dataclip.loc[self.df_dataclip['code']==f'BETA {code}'][lang]
    if cell_value.empty == True:
      return None
    else:
      return cell_value.values[0]

  def get_desc(self, row, lang):
    item_class = self.lookupDictionary(row['CLASS'], lang)
    item_type = self.lookupDictionary(row['TYPE'], lang)
    desc = str(item_class or '') + ' ' + str(item_type or '')
    return desc.strip()

  def preprocess(self, file, processed_dir):
    print(f'{datetime.now()} INFO: Processing institutions ..')
    df_ins = pd.read_csv(file, dtype=str, keep_default_na=False)

    # Class
    self.set_column_value_by_condition(df_ins, 'CLASS.str.len()>0 & CLASS==\'INSTITUTIONS*CLASS*OTHER\'', 'CLASS', '')

    # Description
    df_ins['DESC_EN'] = df_ins.apply (lambda row: self.get_desc(row, 'en'), axis=1)
    df_ins['DESC_ES'] = df_ins.apply (lambda row: self.get_desc(row, 'es'), axis=1)

    # Name edit box
    df_ins['NAME_LANG'] = df_ins.apply (lambda row: self.get_name_lang(row), axis=1)
    df_ins = self.move_last_column_after(df_ins, 'NAME_CLASS')
    df_ins = self.add_new_column_by_condition(df_ins, 'NAME_Q.str.len()>0 & NAME_Q==\'?\'', 'NAME_Q_LABEL', 'Questionable statement')
    df_ins = self.move_last_column_after(df_ins, 'NAME_Q')

    # Milestone edit box
    self.set_column_value_by_condition(df_ins, 'MILESTONE_CLASS.str.len()==0 & (MILESTONE_DETAIL.str.len()>0 | MILESTONE_Q.str.len()>0 | MILESTONE_GEOID.str.len()>0 | MILESTONE_GEOIDQ.str.len()>0 | MILESTONE_BD.str.len()>0 | MILESTONE_BDQ.str.len()>0 | MILESTONE_ED.str.len()>0 | MILESTONE_EDQ.str.len()>0 | MILESTONE_BASIS.str.len()>0)', 'MILESTONE_CLASS', 'Type of event')
    df_ins = self.add_new_column_by_condition(df_ins, 'MILESTONE_Q.str.len()>0 & MILESTONE_Q==\'?\'', 'MILESTONE_Q_LABEL', 'Questionable statement')
    df_ins = self.move_last_column_after(df_ins, 'MILESTONE_Q')
    df_ins = self.add_new_column_by_condition(df_ins, 'MILESTONE_GEOIDQ.str.len()>0 & MILESTONE_GEOIDQ==\'?\'', 'MILESTONE_GEOIDQ_LABEL', 'Questionable statement')
    df_ins = self.move_last_column_after(df_ins, 'MILESTONE_GEOIDQ')

    # Related places
    df_ins = self.add_new_column_by_condition(df_ins, 'RELATED_GEOIDQ.str.len()>0 & RELATED_GEOIDQ==\'?\'', 'RELATED_GEOIDQ_LABEL', 'Questionable statement')
    df_ins = self.move_last_column_after(df_ins, 'RELATED_GEOIDQ')

    # Related institutions
    df_ins = self.add_new_column_by_condition(df_ins, 'RELATED_INSIDQ.str.len()>0 & RELATED_INSIDQ==\'?\'', 'RELATED_INSIDQ_LABEL', 'Questionable statement')
    df_ins = self.move_last_column_after(df_ins, 'RELATED_INSIDQ')

    # Related bibliographies
    df_ins = self.add_new_column_by_condition(df_ins, 'RELATED_BIBCLASS.str.len()>0', 'RELATED_BIBQ_LABEL', 'Catalogue entry')
    df_ins = self.move_last_column_after(df_ins, 'RELATED_BIBCLASS')

    # Related bibliographies
    df_ins = self.add_new_column_by_condition(df_ins, 'RELATED_MANCLASS.str.len()>0', 'RELATED_MANQ_LABEL', 'Mentioned in')
    df_ins = self.move_last_column_after(df_ins, 'RELATED_MANCLASS')

    # Internet edit box
    df_ins = self.add_new_column_from_value(df_ins, 'INTERNET_CLASS', 'UNIVERSAL*INTERNET_CLASS*EMA', 'INTERNET_CLASS_EMA', 'INTERNET_ADDRESS', 'mailto:{value}')
    df_ins = self.move_last_column_after(df_ins, 'INTERNET_CLASS')
    df_ins = self.add_new_column_from_value(df_ins, 'INTERNET_CLASS', 'UNIVERSAL*INTERNET_CLASS*DOI', 'INTERNET_CLASS_DOI', 'INTERNET_ADDRESS')
    df_ins = self.move_last_column_after(df_ins, 'INTERNET_CLASS')
    df_ins = self.add_new_column_from_value(df_ins, 'INTERNET_CLASS', 'UNIVERSAL*INTERNET_CLASS*CAT', 'INTERNET_CLASS_CAT', 'INTERNET_ADDRESS')
    df_ins = self.move_last_column_after(df_ins, 'INTERNET_CLASS')
    df_ins = self.add_new_column_from_value(df_ins, 'INTERNET_CLASS', 'UNIVERSAL*INTERNET_CLASS*URN', 'INTERNET_CLASS_URN', 'INTERNET_ADDRESS')
    df_ins = self.move_last_column_after(df_ins, 'INTERNET_CLASS')
    df_ins = self.add_new_column_from_value(df_ins, 'INTERNET_CLASS', 'UNIVERSAL*INTERNET_CLASS*URI', 'INTERNET_CLASS_URI', 'INTERNET_ADDRESS')
    df_ins = self.move_last_column_after(df_ins, 'INTERNET_CLASS')
    df_ins = self.add_new_column_from_value(df_ins, 'INTERNET_CLASS', 'UNIVERSAL*INTERNET_CLASS*URL', 'INTERNET_CLASS_URL', 'INTERNET_ADDRESS')
    df_ins = self.move_last_column_after(df_ins, 'INTERNET_CLASS')
 
    # Apply safety validations
    self.check_rows_empty_classes(df_ins, ['NAME_CLASS', 'INTERNET_CLASS'])

    df_ins.to_csv(os.path.join(processed_dir, os.path.basename(file)), index=False, quoting=csv.QUOTE_ALL)
    print(f'{datetime.now()} INFO: done')
