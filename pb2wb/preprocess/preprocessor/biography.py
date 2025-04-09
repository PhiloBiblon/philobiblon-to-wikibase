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


SINGLE_PROPERTY_COLUMNS = {
  'Milestones': {'BIOGRAPHY*MILESTONE_CLASS*BOR': 'BOR',
                 'BIOGRAPHY*MILESTONE_CLASS*DIE': 'DIE',
                 'BIOGRAPHY*MILESTONE_CLASS*FLO': 'FLO',
                 'BIOGRAPHY*MILESTONE_CLASS*RES': 'RES',
                 'BIOGRAPHY*MILESTONE_CLASS*VEC': 'VEC',
                 'BIOGRAPHY*MILESTONE_CLASS*VCA': 'VCA',
                 },
  # related persons are modeled in the opposite direction - so we need to know the gender of the object
  'Related_Bio': {# if someone is the father of a female, that female is the daughter of that father
                  'BIOGRAPHY*RELATED_BIOCLASS*FATHER BIOGRAPHY*SEX*F': 'DAUGHTER',
                  # if someone is the father of a male, that male is the son of that father
                  'BIOGRAPHY*RELATED_BIOCLASS*FATHER BIOGRAPHY*SEX*M': 'SON',
                  # and so on
                  'BIOGRAPHY*RELATED_BIOCLASS*MOTHER BIOGRAPHY*SEX*F': 'DAUGHTER',
                  'BIOGRAPHY*RELATED_BIOCLASS*MOTHER BIOGRAPHY*SEX*M': 'SON',
                  'BIOGRAPHY*RELATED_BIOCLASS*SON BIOGRAPHY*SEX*F': 'MOTHER',
                  'BIOGRAPHY*RELATED_BIOCLASS*SON BIOGRAPHY*SEX*M': 'FATHER',
                  'BIOGRAPHY*RELATED_BIOCLASS*DAUGHTER BIOGRAPHY*SEX*F': 'MOTHER',
                  'BIOGRAPHY*RELATED_BIOCLASS*DAUGHTER BIOGRAPHY*SEX*M': 'FATHER',
                  'BIOGRAPHY*RELATED_BIOCLASS*BROTHER BIOGRAPHY*SEX*F': 'SISTER',
                  'BIOGRAPHY*RELATED_BIOCLASS*BROTHER BIOGRAPHY*SEX*M': 'BROTHER',
                  'BIOGRAPHY*RELATED_BIOCLASS*SISTER BIOGRAPHY*SEX*F': 'SISTER',
                  'BIOGRAPHY*RELATED_BIOCLASS*SISTER BIOGRAPHY*SEX*M': 'BROTHER',
                  'BIOGRAPHY*RELATED_BIOCLASS*HUSBAND BIOGRAPHY*SEX*F': 'WIFE',
                  'BIOGRAPHY*RELATED_BIOCLASS*WIFE BIOGRAPHY*SEX*M': 'HUSBAND',
                  # not sure we have any same sex marriages, but just in case...
                  'BIOGRAPHY*RELATED_BIOCLASS*HUSBAND BIOGRAPHY*SEX*M': 'HUSBAND',
                  'BIOGRAPHY*RELATED_BIOCLASS*WIFE BIOGRAPHY*SEX*F': 'WIFE',
                  }
}


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
    # print(row)
    title_number = self.lookupDataclip(row['TITLE_NUMBER'], lang) or ''
    title = self.lookupDataclip(row['TITLE'], lang) or ''
    title_connector = self.lookupDataclip(row['TITLE_CONNECTOR'], lang) or ''
    title_geoid = self.get_value(row['TITLE_GEOID'])
    if title_geoid and title_geoid != 'BETA geoid':
      title_place = places.get(title_geoid, '')
    else:
      title_place = ''
    # print(f'{title_number = }, {title = }, {title_connector = }, {title_place = }')
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

  def self_join_for_related_bio(self, df):
    """
    Join the dataframe to itself to get the SEX of related biographies.

    Args:
        df: Input DataFrame containing biography data

    Returns:
        DataFrame with added RELATED_BIOID_SEX column from self-join
    """
    original_row_count = len(df)

    # Create a temporary df with only non-empty SEX values
    sex_df = df[df['SEX'].notna() & (df['SEX'] != '')][['BIOID', 'SEX']]

    # Perform the join
    result_df = df.merge(
        sex_df,
        left_on='RELATED_BIOID',
        right_on='BIOID',
        how='left',
        suffixes=('', '_object')
    )

    # Verify row count
    if len(result_df) != original_row_count:
        raise ValueError(f"Row count mismatch after join: original={original_row_count}, "
                       f"after join={len(result_df)}. This suggests duplicate BIOIDs in the data.")

    # Rename the joined SEX column to RELATED_BIOID_SEX and drop the extra BIOID column
    result_df = result_df.rename(columns={'SEX_object': 'RELATED_BIOID_SEX'})
    result_df = result_df.drop('BIOID_object', axis=1, errors='ignore')

    result_df = self.move_last_column_after(result_df, 'RELATED_BIOID')

    return result_df

  def preprocess(self):
    print(f'{datetime.now()} INFO: Processing biography ..')

    biography_file = self.get_input_csv(BiographyPreprocessor.TABLE)

    print(f'{datetime.now()} INFO: Input csv: {biography_file}')
    df = pd.read_csv(biography_file, dtype=str, keep_default_na=False)

    df = self.self_join_for_related_bio(df)

    # Add new column combining RELATED_BIOCLASS and RELATED_BIOID_SEX
    df['RELATED_BIOCLASS_WITH_SEX'] = df.apply(
        lambda row: (f"{row['RELATED_BIOCLASS']} {row['RELATED_BIOID_SEX']}"
                    if pd.notna(row['RELATED_BIOID_SEX']) and str(row['RELATED_BIOID_SEX']).strip() != ""
                    else row['RELATED_BIOCLASS']),
        axis=1
    )

    # Move the new column after RELATED_BIOCLASS
    df = self.move_last_column_after(df, 'RELATED_BIOCLASS')

    geography_file = self.get_input_csv(Table.GEOGRAPHY)
    dict_geo = self.load_geo(geography_file)

    df = self.process_defaults_for_editbox(df, BiographyPreprocessor.TABLE.value, 'Milestones')
    df = self.process_defaults_for_editbox(df, BiographyPreprocessor.TABLE.value, 'Titles')
    df = self.process_defaults_for_editbox(df, BiographyPreprocessor.TABLE.value, 'Affiliations')

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

    # add new columns for the qnumbers using the lookup table if supplied
    df = self.add_qnumber_columns(df, BiographyPreprocessor.TABLE)

    # split single properties columns
    df = self.move_single_property_columns(df, SINGLE_PROPERTY_COLUMNS, Table.BIOGRAPHY)

    debug_cols = ['BIOID', 'HUSBAND_RELATED_BIOCLASS_WITH_SEX', 'HUSBAND_RELATED_BIOCLASS', 'HUSBAND_RELATED_BIOCLASS_QNUMBER',
                  'HUSBAND_RELATED_BIODETAIL', 'HUSBAND_RELATED_BIOID', 'HUSBAND_RELATED_BIOID_QNUMBER',
                  'HUSBAND_RELATED_BIOIDQ', 'HUSBAND_RELATED_BIOBD', 'HUSBAND_RELATED_BIOBDQ', 'HUSBAND_RELATED_BIOED',
                  'HUSBAND_RELATED_BIOEDQ', 'HUSBAND_RELATED_BIOBASIS']
    # print only the columns in debug_cols for row with index 193
    # print(f"{datetime.now()} INFO: {df.loc[193, debug_cols]}")


    milestone_primary_column = DATADICT[Table.BIOGRAPHY.value]['Milestones']['primary']
    milestone_secondary_column = DATADICT[Table.BIOGRAPHY.value]['Milestones']['secondary']
    milestone_columns = DATADICT[Table.BIOGRAPHY.value]['Milestones']['columns']

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
