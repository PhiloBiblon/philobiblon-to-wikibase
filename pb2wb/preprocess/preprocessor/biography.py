import os
import pandas as pd
import csv
from datetime import datetime

from common.settings import DATACLIP_DIR
from .generic import GenericPreprocessor

def isfloat(num):
    try:
        float(num)
        return True
    except ValueError:
        return False

class BiographyPreprocessor(GenericPreprocessor):
  DATACLIP_FILENAME = 'beta_dataclips.csv'

  def __init__(self) -> None:
    super().__init__()
    self.df_dataclip = pd.read_csv(os.path.join(DATACLIP_DIR, self.DATACLIP_FILENAME), dtype=str, keep_default_na=False)

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

  def preprocess(self, biography_file, geography_file, processed_dir, qnumber_lookup_file):
    print(f'{datetime.now()} INFO: Processing biography ..')
    # we could load geo to resolve titles e.g. "King of Castille" - but this isn't working yet
    # dict_geo = self.load_geo(geography_file)

    df = pd.read_csv(biography_file, dtype=str, keep_default_na=False)

    # splitting Affiliation_type
    clazz = ['ORD','PRO','REL']
    for c in clazz:
        value = 'BIOGRAPHY*AFFILIATION_CLASS*' + c
        new_col_name = 'AFFILIATION_TYPE_' + c
        df[new_col_name] = (df['AFFILIATION_CLASS'] == value) * 1 * df['AFFILIATION_TYPE']  
        df = self.move_last_column_after(df, 'AFFILIATION_TYPE')

    lookup_df = None
    #lookup_df = pd.read_csv(qnumber_lookup_file, dtype=str, keep_default_na=False)

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
      'SEX',
      'RELATED_BIOCLASS',
      'RELATED_INSCLASS',
      'RELATED_BIBCLASS',
      'RELATED_MANCLASS',
      'INTERNET_CLASS'
    ]

    if lookup_df is not None:
      for field in id_fields + dataclip_fields:
        df = self.add_new_column_from_mapping(df, field, lookup_df, 'PBID', 'QNUMBER', field + '_QNUMBER')
        df = self.move_last_column_after(df, field)

    # expanded title isn't working yet - we can make do with the Moniker
    # df['EXPANDED_TITLE'] = df.apply (lambda row: self.get_expanded_title(row, dict_geo), axis=1)

    # Expanded name is pretty much ok
    df['EXPANDED_NAME'] = df.apply (lambda row: self.get_expanded_name(row), axis=1)

    df.to_csv(os.path.join(processed_dir, os.path.basename(biography_file)), index=False, quoting=csv.QUOTE_ALL)
    print(f'{datetime.now()} INFO: done')
