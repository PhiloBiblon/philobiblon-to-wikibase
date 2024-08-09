from datetime import datetime

import pandas as pd

from common.data_dictionary import DATADICT
from common.enums import Table
from .generic import GenericPreprocessor


class UniformTitlePreprocessor(GenericPreprocessor):
  TABLE = Table.UNIFORM_TITLE

  def __init__(self, top_level_bib=None, qnumber_lookup_file=None) -> None:
    super().__init__(top_level_bib, qnumber_lookup_file)

  def preprocess(self):
    print(f'{datetime.now()} INFO: Processing uniform_title ..')

    file = self.get_input_csv(UniformTitlePreprocessor.TABLE)
    print(f'{datetime.now()} INFO: Input csv: {file}')
    df = pd.read_csv(file, dtype=str, keep_default_na=False)

    # Internet edit box
    df = self.split_internet_class(df)

    # fill in any missing MILESTONE_CLASS values
    key = 'MILESTONE_CLASS'
    cols = DATADICT['uniform_title']['milestones']['columns']
    default_val = DATADICT['uniform_title']['milestones']['default']
    df = self.insert_default_for_missing_key(df.copy(), key, cols, default_val)

    # add new columns for the qnumbers using the lookup table if supplied
    id_fields = DATADICT['uniform_title']['id_fields']
    dataclip_fields = DATADICT['uniform_title']['dataclip_fields']

    df = self.reconcile_base_objects_by_lookup(df, id_fields)
    df = self.reconcile_dataclips_by_lookup(df, dataclip_fields)

    self.write_result_csv(df, file)
    print(f'{datetime.now()} INFO: done')

