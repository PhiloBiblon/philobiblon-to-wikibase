import pandas as pd
from datetime import datetime

from common.enums import Table
from common.data_dictionary import DATADICT
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

  TABLE = Table.INSTITUTIONS

  def __init__(self, top_level_bib=None, qnumber_lookup_file=None, instance=None) -> None:
    super().__init__(top_level_bib, qnumber_lookup_file, instance)

  def get_name_lang(self, row):
    name_class = row['NAME_CLASS']
    if name_class:
      if name_class in self.NAME_CLASS_TO_LANG:
        return self.NAME_CLASS_TO_LANG[name_class]
      else:
        return self.UNKNOWN_LANG
    return ''

  def get_desc(self, row, lang):
    item_class = self.lookupDataclip(row['CLASS'], lang)
    item_type = self.lookupDataclip(row['TYPE'], lang)
    desc = str(item_class or '') + ' ' + str(item_type or '')
    return desc.strip()

  def preprocess(self):
    print(f'{datetime.now()} INFO: Processing institutions ..')

    file = self.get_input_csv(InstitutionPreprocessor.TABLE)
    print(f'{datetime.now()} INFO: Input csv: {file}')
    df_ins = pd.read_csv(file, dtype=str, keep_default_na=False)

    # add new columns for the qnumbers using the lookup table if supplied
    df_ins = self.add_qnumber_columns(df_ins, InstitutionPreprocessor.TABLE)

    # Class
    self.set_column_value_by_condition(df_ins, 'CLASS.str.len()>0 & CLASS==\'INSTITUTIONS*CLASS*OTHER\'', 'CLASS', '')

    # Description
    df_ins['DESC_EN'] = df_ins.apply (lambda row: self.get_desc(row, 'en'), axis=1)
    df_ins['DESC_ES'] = df_ins.apply (lambda row: self.get_desc(row, self.top_level_bib.language_code()), axis=1)

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
    df_ins = self.split_internet_class(df_ins)

    # Apply safety validations
    self.check_rows_empty_classes(df_ins, ['NAME_CLASS', 'INTERNET_CLASS'])

    # truncate any fields that are too long
    df = self.truncate_dataframe(df_ins)

    self.write_result_csv(df_ins, file)
    print(f'{datetime.now()} INFO: done')
