import os
import pandas as pd
import csv
from datetime import datetime

from common.enums import Table
from common.data_dictionary import DATADICT
from .generic import GenericPreprocessor

class LibraryPreprocessor(GenericPreprocessor):

  TABLE = Table.LIBRARY

  def __init__(self, top_level_bib=None, qnumber_lookup_file=None) -> None:
    super().__init__(top_level_bib, qnumber_lookup_file)

  def preprocess(self):
    print(f'{datetime.now()} INFO: Processing library ..')

    file = self.get_input_csv(LibraryPreprocessor.TABLE)
    print(f'{datetime.now()} INFO: Input csv: {file}')
    df = pd.read_csv(file, dtype=str, keep_default_na=False)

    # Internet edit box
    df = self.split_internet_class(df)

    # add new columns for the qnumbers using the lookup table if supplied
    id_fields = DATADICT['library']['id_fields']
    dataclip_fields = DATADICT['library']['dataclip_fields']

    df = self.reconcile_base_objects_by_lookup(df, id_fields)
    df = self.reconcile_dataclips_by_lookup(df, dataclip_fields)

    self.write_result_csv(df, file)
    print(f'{datetime.now()} INFO: done')
