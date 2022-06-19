import os
import pandas as pd
import csv
from .generic import GenericPreprocessor

class BiographyPreprocessor(GenericPreprocessor):
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
    title = self.get_str_value(row['TITLE'])
    title_number = self.get_str_value(row['TITLE_NUMBER'])
    title_connector = self.get_str_value(row['TITLE_CONNECTOR'])
    title_geoid = self.get_value(row['TITLE_GEOID'])
    if title_geoid and title_geoid != 'BETA geoid':
      title_place = places[title_geoid]
    else:
      title_place = None
    return ' '.join(filter(None, [title_number, title, title_connector, title_place])).replace("d’ ", "d’")

  def load_geo(self, geography_file):
    df_geo = pd.read_csv(geography_file, dtype=str)
    df_geo = df_geo[df_geo['NAME_CLASS']=='GEOGRAPHY*NAME_CLASS*U'][['GEOID', 'NAME']]
    return dict(df_geo.values)

  def preprocess(self, biography_file, geography_file, processed_dir):
    dict_geo = self.load_geo(geography_file)

    df_bio = pd.read_csv(biography_file, dtype=str)
    df_bio['EXPANDED_TITLE'] = df_bio.apply (lambda row: self.get_expanded_title(row, dict_geo), axis=1)
    df_bio.to_csv(os.path.join(processed_dir, os.path.basename(biography_file)), index=False, quoting=csv.QUOTE_ALL)
