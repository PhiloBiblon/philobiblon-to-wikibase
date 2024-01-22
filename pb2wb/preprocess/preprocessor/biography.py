import os
import pandas as pd
import csv
from datetime import datetime

from common.enums import Table
from .generic import GenericPreprocessor

def isfloat(num):
    try:
        float(num)
        return True
    except ValueError:
        return False

class BiographyPreprocessor(GenericPreprocessor):
  TABLE = Table.BIOGRAPHY

  def __init__(self, top_level_bib=None, qnumber_lookup_file=None) -> None:
    super().__init__(top_level_bib, qnumber_lookup_file)

  def get_value(self, cell):
    if cell and cell == cell:
      return cell
    else:
      return None

  def get_str_value(self, cell):
    value = self.get_value(cell)
    if value:
      return str(value)
    else:
      return None

  def get_expanded_title(self, row, places):
    # this isn't working yet, and may not be needed...
    title = self.get_str_value(row['TITLE'])
    title_number = self.get_str_value(row['TITLE_NUMBER'])
    title_connector = self.get_str_value(row['TITLE_CONNECTOR'])
    title_geoid = self.get_value(row['TITLE_GEOID'])
    # this is broken since we now have dataclip paths
    if title_geoid and title_geoid != 'BETA geoid':
      title_place = places[title_geoid]
    else:
      title_place = None
    return ' '.join(filter(None, [title_number, title, title_connector, title_place])).replace("d’ ", "d’")

  def get_expanded_name(self, row):
    names = []
    names.append(self.get_str_value(row['NAME_FIRST']))
    names.append(self.get_str_value(row['NAME_LAST']))

    # temporary hack
    name_number = row['NAME_NUMBER']
    if name_number and not isfloat(name_number):
      name_number = name_number[name_number.rfind('*')+1:]
      names.append(name_number)
    # for now, skip the honorific
    # names.append(self.get_str_value(row['NAME_HONORIFIC']))
    names.append(self.get_str_value(row['NAME_EPITHET']))
    return ' '.join(filter(None, names))

  def load_geo(self, geography_file):
    df = pd.read_csv(geography_file, dtype=str)
    df = df[df['NAME_CLASS']=='GEOGRAPHY*NAME_CLASS*U'][['GEOID', 'NAME']]
    return dict(df.values)

  def preprocess(self):
    print(f'{datetime.now()} INFO: Processing biography ..')

    biography_file = self.get_input_csv(BiographyPreprocessor.TABLE)

    print(f'{datetime.now()} INFO: Input csv: {biography_file}')
    df = pd.read_csv(biography_file, dtype=str, keep_default_na=False)

    geography_file = self.get_input_csv(Table.GEOGRAPHY)
    # we could load geo to resolve titles e.g. "King of Castille" - but this isn't working yet
    # dict_geo = self.load_geo(geography_file)

    # Split Affiliation_type
    df = self.split_column_by_clip(df, 'AFFILIATION_CLASS', 'AFFILIATION_TYPE', 'BIOGRAPHY*AFFILIATION_CLASS',
                                   ['ORD', 'PRO', 'REL'])

    # Internet edit box
    df = self.split_internet_class(df)

    # enumerate the pb base item (id) fields
    id_fields = [
      'BIOID',
      'TITLE_GEOID',
      'MILESTONE_GEOID',
      'AFFILIATION_GEOID',
      'RELATED_BIOID',
      'RELATED_INSID',
      'RELATED_BIBID',
      'RELATED_MANID',
      'SUBJECT_GEOID',
      'SUBJECT_INSID',
      'SUBJECT_SUBID'
    ]

    dataclip_fields = [
      'NAME_CLASS',
      'NAME_HONORIFIC',
      'TITLE',
      'TITLE_NUMBER',
      'TITLE_CONNECTOR',
      'MILESTONE_CLASS',
      'AFFILIATION_CLASS',
      'AFFILIATION_TYPE',
      # Note: the next line is columns that were created by the split above
      'AFFILIATION_TYPE_PRO', 'AFFILIATION_TYPE_ORD', 'AFFILIATION_TYPE_REL',
      'SEX',
      'RELATED_BIOCLASS',
      'RELATED_INSCLASS',
      'RELATED_BIBCLASS',
      'RELATED_MANCLASS',
      'INTERNET_CLASS'
    ]

    # add new columns for the qnumbers using the lookup table if supplied
    df = self.reconcile_by_lookup(df, id_fields + dataclip_fields)


    # expanded title isn't working yet - we can top_level_bib do with the Moniker
    # df['EXPANDED_TITLE'] = df.apply (lambda row: self.get_expanded_title(row, dict_geo), axis=1)

    # Expanded name is pretty much ok
    df['EXPANDED_NAME'] = df.apply (lambda row: self.get_expanded_name(row), axis=1)

    self.write_result_csv(df, biography_file)
    print(f'{datetime.now()} INFO: done')
