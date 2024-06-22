import pandas as pd
from datetime import datetime

from common.enums import Table
from .generic import GenericPreprocessor

class AnalyticPreprocessor(GenericPreprocessor):

  TABLE = Table.ANALYTIC

  def __init__(self, top_level_bib=None, qnumber_lookup_file=None) -> None:
    super().__init__(top_level_bib, qnumber_lookup_file)

  def preprocess(self):
    print(f'{datetime.now()} INFO: Processing analytic ..')

    file = self.get_input_csv(AnalyticPreprocessor.TABLE)
    print(f'{datetime.now()} INFO: Input csv: {file}')
    df = pd.read_csv(file, dtype=str, keep_default_na=False)

    # Internet edit box
    df = self.split_internet_class(df)

    # enumerate the pb base item (id) fields
    id_fields = [
      'CNUM',
      'TEXT_MANID',
      'TEXT_UNIID',
      'COMMENT_BIOID',
      'RELATED_BIOID',
      'RELATED_BIBID',
      'RELATED_MANID',
      'RELATED_UNIID',
      'SUBJECT_BIOID',
      'SUBJECT_GEOID',
      'SUBJECT_INSID',
      'SUBJECT_SUBID'
    ]
    dataclip_fields = [
      'DOCUMENT_LANGUAGE',
      'TEXT_LOCCLASS',
      'INC_EXP_CLASS',
      'VARIANT_NAMECLASS',
      'RELATED_BIOCLASS',
      'RELATED_BIBCLASS',
      'RELATED_MANCLASS',
      'RELATED_UNICLASS',
      'STATUS',
      'INTERNET_CLASS'
    ]

    # add new columns for the qnumbers using the lookup table if supplied
    df = self.reconcile_base_objects_by_lookup(df, id_fields)
    df = self.reconcile_dataclips_by_lookup(df, dataclip_fields)

    self.write_result_csv(df, file)
    print(f'{datetime.now()} INFO: done')

