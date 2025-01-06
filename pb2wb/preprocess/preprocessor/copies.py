import os
import pandas as pd
import csv
from datetime import datetime

from common.enums import Table
from common.data_dictionary import DATADICT
from .generic import GenericPreprocessor
from .ms_ed import MsEdPreprocessor

class CopiesPreprocessor(GenericPreprocessor):
  TABLE = Table.COPIES

  def __init__(self, top_level_bib=None, qnumber_lookup_file=None, instance=None) -> None:
    super().__init__(top_level_bib, qnumber_lookup_file, instance)

  def preprocess(self):
    print(f'{datetime.now()} INFO: Processing copies ..')

    file = self.get_input_csv(CopiesPreprocessor.TABLE)
    print(f'{datetime.now()} INFO: Input csv: {file}')
    df = pd.read_csv(file, dtype=str, keep_default_na=False)

    # these editboxes are the same as for ms_ed -- but note that HAND is omitted
    df = self.process_defaults_for_editbox(df, MsEdPreprocessor.TABLE.value, 'related_lib_callnos')
    df = self.process_defaults_for_editbox(df, MsEdPreprocessor.TABLE.value, 'related_lib_events')
    df = self.process_defaults_for_editbox(df, MsEdPreprocessor.TABLE.value, 'sizes')
    df = self.process_defaults_for_editbox(df, MsEdPreprocessor.TABLE.value, 'page_layouts')
    df = self.process_defaults_for_editbox(df, MsEdPreprocessor.TABLE.value, 'fonts')
    df = self.process_defaults_for_editbox(df, MsEdPreprocessor.TABLE.value, 'watermarks')
    df = self.process_defaults_for_editbox(df, MsEdPreprocessor.TABLE.value, 'graphics')
    df = self.process_defaults_for_editbox(df, MsEdPreprocessor.TABLE.value, 'music')
    df = self.process_defaults_for_editbox(df, MsEdPreprocessor.TABLE.value, 'other_features')

    # this one comes from the copies datadict
    df = self.process_defaults_for_editbox(df, CopiesPreprocessor.TABLE.value, 'related_copies')

    # Split RELATED_LIBCALLNO
    df = self.split_column_by_clip(df, 'RELATED_LIBCALLNOCLASS', 'RELATED_LIBCALLNO', 'MS_ED*RELATED_LIBCALLNOCLASS',
                                   ['C', 'F', 'A', 'R', 'B', 'I', 'CIBN45', 'E'])

    # Internet edit box
    df = self.split_internet_class(df)

    # add new columns for the qnumbers using the lookup table if supplied
    df = self.add_qnumber_columns(df, CopiesPreprocessor.TABLE)

    # truncate any fields that are too long
    df = self.truncate_dataframe(df)

    self.write_result_csv(df, file)
    print(f'{datetime.now()} INFO: done')
