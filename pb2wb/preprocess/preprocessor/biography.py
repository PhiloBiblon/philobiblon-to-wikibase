import os
import pandas as pd
import csv
import math
import random

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
    self.runid = random.randint(0,999999)

  def decorate_with_runid(self, s):
    if len(str(s)) == 0:
      return s
    return f'{self.runid} {s}'

  def quote_string(self, s):
    return f'"{s}"'

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

  def make_label(self, row):
    return row['BIOID'] if len(row['EXPANDED_NAME']) == 0 else row['EXPANDED_NAME']

  def make_desc(self, row):
    if row['EXPANDED_NAME'] != row['MONIKER']:
      return row['MONIKER']
    return ""

  def preprocess(self, biography_file, geography_file, processed_dir):
    print('INFO: Processing biography ..')
    # we could load geo to resolve titles e.g. "King of Castille" - but this isn't working yet
    # dict_geo = self.load_geo(geography_file)

    df = pd.read_csv(biography_file, dtype=str, keep_default_na=False)

    # explanded title isn't working yet - we can make do with the Moniker
    # df['EXPANDED_TITLE'] = df.apply (lambda row: self.get_expanded_title(row, dict_geo), axis=1)

    # Expanded name is pretty much ok
    df['EXPANDED_NAME'] = df.apply (lambda row: self.get_expanded_name(row), axis=1)

    # Create columns for direct consumption by quickstatements csv
    df['Len'] = df.apply (lambda row: self.decorate_with_runid(self.make_label(row)), axis=1)
    df['Den'] = df.apply (lambda row: self.decorate_with_runid(self.make_desc(row)), axis=1)
    df['Aen'] = df.apply (lambda row: self.decorate_with_runid(row["BIOID"]), axis=1)
    df['P-PBID'] = df.apply (lambda row: self.quote_string(row["BIOID"]), axis=1)

    df.to_csv(os.path.join(processed_dir, os.path.basename(biography_file)), index=False, quoting=csv.QUOTE_ALL)
    print('INFO: done.')
