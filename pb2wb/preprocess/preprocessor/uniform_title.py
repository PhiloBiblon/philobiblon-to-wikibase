from datetime import datetime

import pandas as pd

from common.data_dictionary import DATADICT
from common.enums import Table
from .generic import GenericPreprocessor


class UniformTitlePreprocessor(GenericPreprocessor):
  TABLE = Table.UNIFORM_TITLE

  def __init__(self, top_level_bib=None, qnumber_lookup_file=None, instance=None) -> None:
    super().__init__(top_level_bib, qnumber_lookup_file, instance)

  def preprocess(self):
    print(f'{datetime.now()} INFO: Processing uniform_title ..')

    file = self.get_input_csv(UniformTitlePreprocessor.TABLE)
    print(f'{datetime.now()} INFO: Input csv: {file}')
    df = pd.read_csv(file, dtype=str, keep_default_na=False)

    # Internet edit box
    df = self.split_internet_class(df)

    df = self.process_defaults_for_editbox(df, UniformTitlePreprocessor.TABLE.value, 'Incipits & Explicits')
    df = self.process_defaults_for_editbox(df, UniformTitlePreprocessor.TABLE.value, 'Milestones')

    # add new columns for the qnumbers using the lookup table if supplied
    df = self.add_qnumber_columns(df, UniformTitlePreprocessor.TABLE)

    # truncate any fields that are too long
    df = self.truncate_dataframe(df)

    self.write_result_csv(df, file)
    print(f'{datetime.now()} INFO: done')

