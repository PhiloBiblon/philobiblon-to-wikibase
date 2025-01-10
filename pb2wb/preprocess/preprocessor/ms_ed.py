from datetime import datetime

import pandas as pd

from common.data_dictionary import DATADICT
from common.enums import Table
from .generic import GenericPreprocessor

class MsEdPreprocessor(GenericPreprocessor):
  TABLE = Table.MS_ED

  def __init__(self, top_level_bib=None, qnumber_lookup_file=None, instance=None) -> None:
    super().__init__(top_level_bib, qnumber_lookup_file, instance)

  def preprocess(self):
    print(f'{datetime.now()} INFO: Processing ms_ed ..')

    file = self.get_input_csv(MsEdPreprocessor.TABLE)
    print(f'{datetime.now()} INFO: Input csv: {file}')
    df = pd.read_csv(file, dtype=str, keep_default_na=False)

    # propagate the MILESTONE_CLASS through enlargers
    key_columns = ['MANID', 'MILESTONE_MAKER_IDP']
    columns_to_propagate = ['MILESTONE_CLASS']
    df = self.propagate_enlarger(df, key_columns, columns_to_propagate)

    # fill in any remaining missing MILESTONE_CLASS values
    df = self.process_defaults_for_editbox(df, MsEdPreprocessor.TABLE.value, 'Milestones')

    # Fill in all editbox initial columns that need defaults
    df = self.process_defaults_for_editbox(df, MsEdPreprocessor.TABLE.value, 'Call Numbers')
    df = self.process_defaults_for_editbox(df, MsEdPreprocessor.TABLE.value, 'History')
    df = self.process_defaults_for_editbox(df, MsEdPreprocessor.TABLE.value, 'Size')
    df = self.process_defaults_for_editbox(df, MsEdPreprocessor.TABLE.value, 'Page Layout')
    df = self.process_defaults_for_editbox(df, MsEdPreprocessor.TABLE.value, 'Hands')
    df = self.process_defaults_for_editbox(df, MsEdPreprocessor.TABLE.value, 'Fonts')
    df = self.process_defaults_for_editbox(df, MsEdPreprocessor.TABLE.value, 'Watermarks')
    df = self.process_defaults_for_editbox(df, MsEdPreprocessor.TABLE.value, 'Graphics')
    df = self.process_defaults_for_editbox(df, MsEdPreprocessor.TABLE.value, 'Music')
    df = self.process_defaults_for_editbox(df, MsEdPreprocessor.TABLE.value, 'Other features')
    df = self.process_defaults_for_editbox(df, MsEdPreprocessor.TABLE.value, 'Related Uniform Titles')
    df = self.process_defaults_for_editbox(df, MsEdPreprocessor.TABLE.value, 'Related Individuals')
    df = self.process_defaults_for_editbox(df, MsEdPreprocessor.TABLE.value, 'Related manuscripts')

    # Split RELATED_LIBCALLNO
    df = self.split_column_by_clip(df, 'RELATED_LIBCALLNOCLASS', 'RELATED_LIBCALLNO', 'MS_ED*RELATED_LIBCALLNOCLASS',
                                   ['C', 'F', 'A', 'R', 'B', 'I', 'CIBN45', 'E'])

    # split MILESTONE columns by ms vs. ed
    # Split MILESTONE_MAKER
    df = self.split_column_by_clip(df, 'MILESTONE_CLASS', 'MILESTONE_MAKER_ID', 'MS_ED*MILESTONE_CLASS',
                                   ['P', 'W'])
    # Split MILESTONE_GEOID
    df = self.split_column_by_clip(df, 'MILESTONE_CLASS', 'MILESTONE_GEOID', 'MS_ED*MILESTONE_CLASS',
                                   ['P', 'W'])
    # Split MILESTONE_BD
    df = self.split_column_by_clip(df, 'MILESTONE_CLASS', 'MILESTONE_BD', 'MS_ED*MILESTONE_CLASS',
                                   ['P', 'W'])
    # Split MILESTONE_BDQ
    df = self.split_column_by_clip(df, 'MILESTONE_CLASS', 'MILESTONE_BDQ', 'MS_ED*MILESTONE_CLASS',
                                   ['P', 'W'])
    # Split MILESTONE_ED
    df = self.split_column_by_clip(df, 'MILESTONE_CLASS', 'MILESTONE_ED', 'MS_ED*MILESTONE_CLASS',
                                   ['P', 'W'])
    # Split MILESTONE_EDQ
    df = self.split_column_by_clip(df, 'MILESTONE_CLASS', 'MILESTONE_EDQ', 'MS_ED*MILESTONE_CLASS',
                                   ['P', 'W'])
    # Split MILESTONE_BASIS
    df = self.split_column_by_clip(df, 'MILESTONE_CLASS', 'MILESTONE_BASIS', 'MS_ED*MILESTONE_CLASS',
                                   ['P', 'W'])

    # Split MILESTONE_CLASS
    df = self.split_column_by_clip(df, 'MILESTONE_CLASS', 'MILESTONE_CLASS', 'MS_ED*MILESTONE_CLASS',
                                   ['P', 'W'])

    # Internet edit box
    df = self.split_internet_class(df)

    # add new columns for the qnumbers using the lookup table if supplied
    df = self.add_qnumber_columns(df, MsEdPreprocessor.TABLE)

    # truncate any fields that are too long
    df = self.truncate_dataframe(df)

    self.write_result_csv(df, file)
    print(f'{datetime.now()} INFO: done')
