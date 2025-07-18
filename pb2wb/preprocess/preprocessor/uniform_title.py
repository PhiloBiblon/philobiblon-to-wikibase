from datetime import datetime

import pandas as pd

from common.data_dictionary import DATADICT
from common.enums import Table
from .generic import GenericPreprocessor


class UniformTitlePreprocessor(GenericPreprocessor):
  TABLE = Table.UNIFORM_TITLE

  def __init__(self, top_level_bib=None, qnumber_lookup_file=None, instance=None) -> None:
    super().__init__(top_level_bib, qnumber_lookup_file, instance)

    self.SINGLE_PROPERTY_COLUMNS = {
      'Milestones': {'UNIFORM_TITLE*MILESTONE_CLASS*W': 'WRITTEN',
                     'UNIFORM_TITLE*MILESTONE_CLASS*E': 'PUBLISHED',  # BETA
                     #'UNIFORM_TITLE*MILESTONE_CLASS*I': 'PUBLISHED',  # BITAGAP
                   },
      'Related_Bio': {'UNIFORM_TITLE*RELATED_BIOCLASS*TRANSLATOR': 'TRANSLATOR',
                    }
    }

  def preprocess(self):
    print(f'{datetime.now()} INFO: Processing uniform_title ..')

    bib_name = str(self.top_level_bib).split('.')[-1]
    print(bib_name)
    if bib_name in ['BITECA', 'BITAGAP']:
        SINGLE_PROPERTY_COLUMNS = {
            section: {
                key.replace('UNIFORM_TITLE', f'{bib_name.upper()} UNIFORM_TITLE', 1): value
                for key, value in mappings.items()
            }
            for section, mappings in self.SINGLE_PROPERTY_COLUMNS.items()
        }

    file = self.get_input_csv(UniformTitlePreprocessor.TABLE)
    print(f'{datetime.now()} INFO: Input csv: {file}')
    df = pd.read_csv(file, dtype=str, keep_default_na=False)

    # Internet edit box
    df = self.split_internet_class(df)

    df = self.process_defaults_for_editbox(df, UniformTitlePreprocessor.TABLE.value, 'Incipits & Explicits')
    df = self.process_defaults_for_editbox(df, UniformTitlePreprocessor.TABLE.value, 'Milestones')

    # add new columns for the qnumbers using the lookup table if supplied
    df = self.add_qnumber_columns(df, UniformTitlePreprocessor.TABLE)

    # split single properties columns
    df = self.move_single_property_columns(df, SINGLE_PROPERTY_COLUMNS, UniformTitlePreprocessor.TABLE)

    # truncate any fields that are too long
    df = self.truncate_dataframe(df)

    self.write_result_csv(df, file)
    print(f'{datetime.now()} INFO: done')

