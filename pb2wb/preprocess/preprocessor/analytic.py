import pandas as pd
from datetime import datetime

from common.enums import Table
from common.data_dictionary import DATADICT

from .generic import GenericPreprocessor

class AnalyticPreprocessor(GenericPreprocessor):

  TABLE = Table.ANALYTIC

  def __init__(self, top_level_bib=None, qnumber_lookup_file=None, instance=None) -> None:
    super().__init__(top_level_bib, qnumber_lookup_file, instance)

  def preprocess(self):
    print(f'{datetime.now()} INFO: Processing analytic ..')

    file = self.get_input_csv(AnalyticPreprocessor.TABLE)
    print(f'{datetime.now()} INFO: Input csv: {file}')
    df = pd.read_csv(file, dtype=str, keep_default_na=False)

    df = self.process_defaults_for_editbox(df, AnalyticPreprocessor.TABLE.value, 'Incipits & Explicits')

    # Make sure the TEXT_MANID and TEXT_SEQUENCE are populated in any row in which TEXT_LOC is non-empty
    df = self.propagate_values_in_groups(df, 'CNUM', ['TEXT_MANID', 'TEXT_SEQUENCE'],
                                         'TEXT_LOC')

    # Internet edit box
    df = self.split_internet_class(df)

    # add new columns for the qnumbers using the lookup table if supplied
    df = self.add_qnumber_columns(df, AnalyticPreprocessor.TABLE)

    # truncate any fields that are too long
    df = self.truncate_dataframe(df)

    self.write_result_csv(df, file)
    print(f'{datetime.now()} INFO: done')

