import os
import pandas as pd
import csv
from datetime import datetime

from common.enums import Table
from common.data_dictionary import DATADICT
from .generic import GenericPreprocessor

class LibraryPreprocessor(GenericPreprocessor):

  TABLE = Table.LIBRARY

  def format_library_address(self, row):
    cnames = ['ADDRESS', 'PCODE', 'CITY', 'STATE', 'COUNTRY']
    components = {n: row[n] for n in cnames}
    if all(value is None or value == '' for value in components.values()):
      result = ''
    else:
      components['STATE'] = f"({components['STATE']})" if components['STATE'] is not None and len(
        components['STATE']) > 0 else components['STATE']
      components = [components[n] for n in cnames if components[n] is not None and len(components[n]) > 0]
      result = ' '.join(components)
    return result

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
    df = self.add_qnumber_columns(df, LibraryPreprocessor.TABLE)

    df['FULL_ADDRESS'] = df.apply(self.format_library_address, axis=1)
    df = self.move_last_column_after(df, 'PCODE')

    self.write_result_csv(df, file)
    print(f'{datetime.now()} INFO: done')
