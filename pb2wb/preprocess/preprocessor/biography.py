from datetime import datetime

import numpy as np
import pandas as pd

from common.data_dictionary import DATADICT
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

  def __init__(self, top_level_bib=None, qnumber_lookup_file=None, instance=None) -> None:
    super().__init__(top_level_bib, qnumber_lookup_file, instance)

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

  def get_expanded_title(self, row, places, lang):
    title = self.lookupDataclip(row['TITLE'], lang) or ''
    title_connector = self.lookupDataclip(row['TITLE_CONNECTOR'], lang) or ''
    title_geoid = self.get_value(row['TITLE_GEOID'])
    if title_geoid and title_geoid != 'BETA geoid':
      title_place = places.get(title_geoid, '')
    else:
      title_place = ''
    return ' '.join(filter(None, [title, title_connector, title_place])).replace("d’ ", "d’")

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
    dict_geo = self.load_geo(geography_file)

    # fill in any missing MILESTONE_CLASS values
    key = 'MILESTONE_CLASS'
    cols = DATADICT[BiographyPreprocessor.TABLE.value]['milestones']['columns']
    default_val = DATADICT[BiographyPreprocessor.TABLE.value]['milestones']['default']
    df = self.insert_default_for_missing_key(df.copy(), key, cols, default_val)

    # Split Affiliation_type
    df = self.split_column_by_clip(df, 'AFFILIATION_CLASS', 'AFFILIATION_TYPE', 'BIOGRAPHY*AFFILIATION_CLASS',
                                   ['ORD', 'PRO', 'REL'])

    # Internet edit box
    df = self.split_internet_class(df)

    # Split related_biod
    # this list will need to be modified for the non-BETA bibliographies
    related_object_clips = [
      "BIOGRAPHY*RELATED_BIOCLASS*<ALB",
      "BIOGRAPHY*RELATED_BIOCLASS*<ALF",
      "BIOGRAPHY*RELATED_BIOCLASS*<CANC",
      "BIOGRAPHY*RELATED_BIOCLASS*<CAP",
      "BIOGRAPHY*RELATED_BIOCLASS*<COP",
      "BIOGRAPHY*RELATED_BIOCLASS*<CRON",
      "BIOGRAPHY*RELATED_BIOCLASS*<DAMA",
      "BIOGRAPHY*RELATED_BIOCLASS*<EMB",
      "BIOGRAPHY*RELATED_BIOCLASS*<HALC",
      "BIOGRAPHY*RELATED_BIOCLASS*<HER",
      "BIOGRAPHY*RELATED_BIOCLASS*<LEG",
      "BIOGRAPHY*RELATED_BIOCLASS*<MISTRESS",
      "BIOGRAPHY*RELATED_BIOCLASS*<NOT",
      "BIOGRAPHY*RELATED_BIOCLASS*<OFI",
      "BIOGRAPHY*RELATED_BIOCLASS*<PARTIDARIA",
      "BIOGRAPHY*RELATED_BIOCLASS*<PARTIDARIO",
      "BIOGRAPHY*RELATED_BIOCLASS*<PRO",
      "BIOGRAPHY*RELATED_BIOCLASS*<REYARMAS",
      "BIOGRAPHY*RELATED_BIOCLASS*<SCR",
      "BIOGRAPHY*RELATED_BIOCLASS*<SEC",
      "BIOGRAPHY*RELATED_BIOCLASS*<TRNCH",
      "BIOGRAPHY*RELATED_BIOCLASS*ACONSJA",
      "BIOGRAPHY*RELATED_BIOCLASS*ACONSJO",
      "BIOGRAPHY*RELATED_BIOCLASS*APPRENTICE",
      "BIOGRAPHY*RELATED_BIOCLASS*ASESINADO",
      "BIOGRAPHY*RELATED_BIOCLASS*COMENTO",
      "BIOGRAPHY*RELATED_BIOCLASS*CONFA",
      "BIOGRAPHY*RELATED_BIOCLASS*CONFO",
      "BIOGRAPHY*RELATED_BIOCLASS*PREDO",
      "BIOGRAPHY*RELATED_BIOCLASS*REGTADA",
      "BIOGRAPHY*RELATED_BIOCLASS*REGTADO",
      "BIOGRAPHY*RELATED_BIOCLASS*SUBO",
      "BIOGRAPHY*RELATED_BIOCLASS*TUTELADO"
    ]

    subject_object_predicate = lambda row: row['RELATED_BIOCLASS'] in related_object_clips
    df = self.split_column_by_predicate(df, 'RELATED_BIOID', subject_object_predicate,
                                        true_extension='OBJECT', false_extension='SUBJECT')

    # enumerate the pb base item (id) fields

    # add new columns for the qnumbers using the lookup table if supplied
    df = self.add_qnumber_columns(df, BiographyPreprocessor.TABLE)

    milestone_primary_column = 'MILESTONE_CLASS'
    milestone_secondary_column = 'MILESTONE_DETAIL'
    milestone_columns = [
      'MILESTONE_Q',
      'MILESTONE_GEOID',
      'MILESTONE_GEOIDQ',
      'MILESTONE_BD',
      'MILESTONE_BDQ',
      'MILESTONE_ED',
      'MILESTONE_EDQ',
      'MILESTONE_BASIS'
    ]
    milestone_default_secondary_nonempty = "EVENT"
    milestone_default_empty_secondary = "RES"

    # if both the primary and secondary are empty, but at least one other column is non-empty,
    # we use the "milestone_default_empty_secondary"
    df[milestone_primary_column] = (
      np.where(((df[milestone_primary_column] == '') &
                (df[milestone_secondary_column] == '') &
                (df[milestone_columns].replace('', np.nan).notna().any(axis=1))),
               milestone_default_empty_secondary, df[milestone_primary_column]))

    # if the primary is empty but the secondary is not, we use the "milestone_default_secondary_nonempty"
    df[milestone_primary_column] = (
      np.where(((df[milestone_primary_column] == '') &
                (df[milestone_secondary_column] != '')),
               milestone_default_secondary_nonempty, df[milestone_primary_column]))

    df['EXPANDED_TITLE_EN'] = df.apply (lambda row: self.get_expanded_title(row, dict_geo, 'en'), axis=1)
    df = self.move_last_column_after(df, 'TITLE_BASIS')
    df['EXPANDED_TITLE_U'] = df.apply (lambda row: self.get_expanded_title(row, dict_geo, self.top_level_bib.language_code()), axis=1)
    df = self.move_last_column_after(df, 'EXPANDED_TITLE_EN')

    # Expanded name is pretty much ok
    df['EXPANDED_NAME'] = df.apply (lambda row: self.get_expanded_name(row), axis=1)

    # truncate any fields that are too long
    df = self.truncate_dataframe(df)

    self.write_result_csv(df, biography_file)
    print(f'{datetime.now()} INFO: done')
