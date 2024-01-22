import os
import pandas as pd
import csv
from datetime import datetime

from common.enums import Table
from .generic import GenericPreprocessor

class BibliographyPreprocessor(GenericPreprocessor):

  TABLE = Table.BIBLIOGRAPHY

  def __init__(self, top_level_bib=None, qnumber_lookup_file=None) -> None:
    super().__init__(top_level_bib, qnumber_lookup_file)

  def preprocess(self):
    print(f'{datetime.now()} INFO: Processing bibliography ..')

    file = self.get_input_csv(BibliographyPreprocessor.TABLE)
    print(f'{datetime.now()} INFO: Input csv: {file}')
    df = pd.read_csv(file, dtype=str, keep_default_na=False)
    
    df['CREATOR_FULLNAME'] = df['CREATOR_FNAME'] + ' ' + df['CREATOR_LNAME']
    df = self.move_last_column_after(df, 'CREATOR_LNAME')
      
    df['ADJUNCT_FULLNAME'] = df['ADJUNCT_FNAME'] + ' ' + df['ADJUNCT_LNAME']
    df = self.move_last_column_after(df, 'ADJUNCT_LNAME')

    # Internet edit box
    df = self.split_internet_class(df)

    # Split ID_NUMBER
    df = self.split_column_by_clip(df, 'ID_CLASS', 'ID_NUMBER', 'BIBLIOGRAPHY*ID_CLASS',
                                   ['DOI', 'EISBN', 'ISBN', 'ISBN-10', 'ISBN-13', 'ISSN', 'ISSN-E'])

    # enumerate the pb base item (id) fields
    id_fields = [
      'BIBID',
      'RELATED_LIBID',
      'RELATED_BIBID',
      'SUBJECT_BIOID',
      'SUBJECT_GEOID',
      'SUBJECT_INSID',
      'SUBJECT_SUBID'
    ]

    dataclip_fields = [
      'CREATOR_ROLE',
      'ADJUNCT_ROLE',
      'LOCATION_CLASS',
      'ID_CLASS',
      'FORM',
      'TYPE',
      'MEDIUM',
      'CLASS',
      'STATUS',
      'RELATED_BIBCLASS',
      'INTERNET_CLASS'
    ]

    # add new columns for the qnumbers using the lookup table if supplied
    df = self.reconcile_by_lookup(df, id_fields + dataclip_fields)

    self.write_result_csv(df, file)
    print(f'{datetime.now()} INFO: done')
