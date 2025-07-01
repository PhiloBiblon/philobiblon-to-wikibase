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
                 'BIOGRAPHY*MILESTONE_CLASS*NAT': 'BOR',
                 'BIOGRAPHY*MILESTONE_CLASS*NATA': 'BOR',
                 'BIOGRAPHY*MILESTONE_CLASS*NATO': 'BOR',
                 'BIOGRAPHY*MILESTONE_CLASS*DIE': 'DIE',
                 'BIOGRAPHY*MILESTONE_CLASS*FLO': 'FLO',
                 'BIOGRAPHY*MILESTONE_CLASS*RES': 'RES',
                 'BIOGRAPHY*MILESTONE_CLASS*MOR': 'RES',
                 'BIOGRAPHY*MILESTONE_CLASS*MORA': 'RES',
                 'BIOGRAPHY*MILESTONE_CLASS*MORB': 'RES',
                 'BIOGRAPHY*MILESTONE_CLASS*MORO': 'RES',
                 'BIOGRAPHY*MILESTONE_CLASS*MORON': 'RES',
                 'BIOGRAPHY*MILESTONE_CLASS*MORONA': 'RES',
                 'BIOGRAPHY*MILESTONE_CLASS*VIZI': 'RES',
                 'BIOGRAPHY*MILESTONE_CLASS*VEC': 'VEC',
                 'BIOGRAPHY*MILESTONE_CLASS*VCA': 'VCA',
                 },
  # related persons are modeled in the opposite direction - so we need to know the gender of the object
  'Related_Bio': {# if someone is the father of a female, that female is the daughter of that father
        'BETA': {
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
                  },
        'BITAGAP': {
                'BIOGRAPHY*RELATED_BIOCLASS*PAI BIOGRAPHY*SEX*F': 'DAUGHTER',
                'BIOGRAPHY*RELATED_BIOCLASS*PAI BIOGRAPHY*SEX*M': 'SON',
                'BIOGRAPHY*RELATED_BIOCLASS*MÃE BIOGRAPHY*SEX*F': 'DAUGHTER',
                'BIOGRAPHY*RELATED_BIOCLASS*MÃE BIOGRAPHY*SEX*M': 'SON',
                'BIOGRAPHY*RELATED_BIOCLASS*FILHO BIOGRAPHY*SEX*F': 'MOTHER',
                'BIOGRAPHY*RELATED_BIOCLASS*FILHO BIOGRAPHY*SEX*M': 'FATHER',
                'BIOGRAPHY*RELATED_BIOCLASS*FILHA BIOGRAPHY*SEX*F': 'MOTHER',
                'BIOGRAPHY*RELATED_BIOCLASS*FILHA BIOGRAPHY*SEX*M': 'FATHER',
                'BIOGRAPHY*RELATED_BIOCLASS*FFLO BIOGRAPHY*SEX*F': 'MOTHER',
                'BIOGRAPHY*RELATED_BIOCLASS*FFLO BIOGRAPHY*SEX*M': 'FATHER',
                'BIOGRAPHY*RELATED_BIOCLASS*FFLA BIOGRAPHY*SEX*F': 'MOTHER',
                'BIOGRAPHY*RELATED_BIOCLASS*FFLA BIOGRAPHY*SEX*M': 'FATHER',
                'BIOGRAPHY*RELATED_BIOCLASS*FFNA BIOGRAPHY*SEX*F': 'MOTHER',
                'BIOGRAPHY*RELATED_BIOCLASS*FFNA BIOGRAPHY*SEX*M': 'FATHER',
                'BIOGRAPHY*RELATED_BIOCLASS*FFNAO BIOGRAPHY*SEX*F': 'MOTHER',
                'BIOGRAPHY*RELATED_BIOCLASS*FFNAO BIOGRAPHY*SEX*M': 'FATHER',
                'BIOGRAPHY*RELATED_BIOCLASS*FFNO BIOGRAPHY*SEX*F': 'MOTHER',
                'BIOGRAPHY*RELATED_BIOCLASS*FFNO BIOGRAPHY*SEX*M': 'FATHER',
                'BIOGRAPHY*RELATED_BIOCLASS*FFNOO BIOGRAPHY*SEX*F': 'MOTHER',
                'BIOGRAPHY*RELATED_BIOCLASS*FFNOO BIOGRAPHY*SEX*M': 'FATHER',
                'BIOGRAPHY*RELATED_BIOCLASS*PAI3 BIOGRAPHY*SEX*F': 'DAUGHTER',
                'BIOGRAPHY*RELATED_BIOCLASS*PAI3 BIOGRAPHY*SEX*M': 'SON',
                'BIOGRAPHY*RELATED_BIOCLASS*PAI4 BIOGRAPHY*SEX*F': 'DAUGHTER',
                'BIOGRAPHY*RELATED_BIOCLASS*PAI4 BIOGRAPHY*SEX*M': 'SON',
                'BIOGRAPHY*RELATED_BIOCLASS*PAI5 BIOGRAPHY*SEX*F': 'DAUGHTER',
                'BIOGRAPHY*RELATED_BIOCLASS*PAI5 BIOGRAPHY*SEX*M': 'SON',
                'BIOGRAPHY*RELATED_BIOCLASS*PPAAII BIOGRAPHY*SEX*F': 'DAUGHTER',
                'BIOGRAPHY*RELATED_BIOCLASS*PPAAII BIOGRAPHY*SEX*M': 'SON',
                'BIOGRAPHY*RELATED_BIOCLASS*PPAI BIOGRAPHY*SEX*F': 'DAUGHTER',
                'BIOGRAPHY*RELATED_BIOCLASS*PPAI BIOGRAPHY*SEX*M': 'SON',
                'BIOGRAPHY*RELATED_BIOCLASS*MAE3 BIOGRAPHY*SEX*F': 'DAUGHTER',
                'BIOGRAPHY*RELATED_BIOCLASS*MAE3 BIOGRAPHY*SEX*M': 'SON',
                'BIOGRAPHY*RELATED_BIOCLASS*MAE4 BIOGRAPHY*SEX*F': 'DAUGHTER',
                'BIOGRAPHY*RELATED_BIOCLASS*MAE4 BIOGRAPHY*SEX*M': 'SON',
                'BIOGRAPHY*RELATED_BIOCLASS*MAAEE BIOGRAPHY*SEX*F': 'DAUGHTER',
                'BIOGRAPHY*RELATED_BIOCLASS*MAAEE BIOGRAPHY*SEX*M': 'SON',
                'BIOGRAPHY*RELATED_BIOCLASS*IRMÃO BIOGRAPHY*SEX*F': 'SISTER',
                'BIOGRAPHY*RELATED_BIOCLASS*IRMÃO BIOGRAPHY*SEX*M': 'BROTHER',
                'BIOGRAPHY*RELATED_BIOCLASS*IRMÃ BIOGRAPHY*SEX*F': 'SISTER',
                'BIOGRAPHY*RELATED_BIOCLASS*IRMÃ BIOGRAPHY*SEX*M': 'BROTHER',
                'BIOGRAPHY*RELATED_BIOCLASS*MARIDO BIOGRAPHY*SEX*F': 'WIFE',
                'BIOGRAPHY*RELATED_BIOCLASS*ESPOSA BIOGRAPHY*SEX*M': 'HUSBAND',
                'BIOGRAPHY*RELATED_BIOCLASS*ESPÔSA BIOGRAPHY*SEX*M': 'HUSBAND',
                'BIOGRAPHY*RELATED_BIOCLASS*MARIDO BIOGRAPHY*SEX*M': 'HUSBAND',
                'BIOGRAPHY*RELATED_BIOCLASS*ESPOSA BIOGRAPHY*SEX*F': 'WIFE',
        },
        'BITECA': {
                'BIOGRAPHY*RELATED_BIOCLASS*PARE BIOGRAPHY*SEX*F': 'DAUGHTER',
                'BIOGRAPHY*RELATED_BIOCLASS*PARE BIOGRAPHY*SEX*M': 'SON',
                'BIOGRAPHY*RELATED_BIOCLASS*MARE BIOGRAPHY*SEX*F': 'DAUGHTER',
                'BIOGRAPHY*RELATED_BIOCLASS*MARE BIOGRAPHY*SEX*M': 'SON',
                'BIOGRAPHY*RELATED_BIOCLASS*FILL BIOGRAPHY*SEX*F': 'MOTHER',
                'BIOGRAPHY*RELATED_BIOCLASS*FILL BIOGRAPHY*SEX*M': 'FATHER',
                'BIOGRAPHY*RELATED_BIOCLASS*FILLA BIOGRAPHY*SEX*F': 'MOTHER',
                'BIOGRAPHY*RELATED_BIOCLASS*FILLA BIOGRAPHY*SEX*M': 'FATHER',
                'BIOGRAPHY*RELATED_BIOCLASS*GERMÀ BIOGRAPHY*SEX*F': 'SISTER',
                'BIOGRAPHY*RELATED_BIOCLASS*GERMÀ BIOGRAPHY*SEX*M': 'BROTHER',
                'BIOGRAPHY*RELATED_BIOCLASS*GERMANA BIOGRAPHY*SEX*F': 'SISTER',
                'BIOGRAPHY*RELATED_BIOCLASS*GERMANA BIOGRAPHY*SEX*M': 'BROTHER',
                'BIOGRAPHY*RELATED_BIOCLASS*MARIT BIOGRAPHY*SEX*F': 'WIFE',
                'BIOGRAPHY*RELATED_BIOCLASS*MULLER BIOGRAPHY*SEX*M': 'HUSBAND',
                'BIOGRAPHY*RELATED_BIOCLASS*MARIT BIOGRAPHY*SEX*M': 'HUSBAND',
                'BIOGRAPHY*RELATED_BIOCLASS*MULLER BIOGRAPHY*SEX*F': 'WIFE'
        }
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
    title_number = title = title_connector = title_place = ''
    if title_num_clip := row.get('TITLE_NUMBER'):
        title_number = self.lookupDataclip(title_num_clip, lang) or ''
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
    related_object_clips = {
      "BETA": [
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
      ],
      "BITAGAP": [
        "BITAGAP BIOGRAPHY*RELATED_BIOCLASS<ALFERES"
        "BITAGAP BIOGRAPHY*RELATED_BIOCLASS<CAP"
        "BITAGAP BIOGRAPHY*RELATED_BIOCLASS<CHANCELER"
        "BITAGAP BIOGRAPHY*RELATED_BIOCLASS<CAPEL"
        "BITAGAP BIOGRAPHY*RELATED_BIOCLASS<COP"
        "BITAGAP BIOGRAPHY*RELATED_BIOCLASS<CRONISTA"
        "BITAGAP BIOGRAPHY*RELATED_BIOCLASS<DAMADECOMPANHIA"
        "BITAGAP BIOGRAPHY*RELATED_BIOCLASS<EMB"
        "BITAGAP BIOGRAPHY*RELATED_BIOCLASS<ESCRIVÃ"
        "BITAGAP BIOGRAPHY*RELATED_BIOCLASS<FALCOEIRO"
        "BITAGAP BIOGRAPHY*RELATED_BIOCLASS<ARAUTO"
        "BITAGAP BIOGRAPHY*RELATED_BIOCLASS<BAR"
        "BITAGAP BIOGRAPHY*RELATED_BIOCLASS<NOTAR"
        "BITAGAP BIOGRAPHY*RELATED_BIOCLASS<PAR"
        "BITAGAP BIOGRAPHY*RELATED_BIOCLASS<PAR"
        "BITAGAP BIOGRAPHY*RELATED_BIOCLASS<PROC"
        "BITAGAP BIOGRAPHY*RELATED_BIOCLASS<REARS "
        "BITAGAP BIOGRAPHY*RELATED_BIOCLASS<ESCRIVÃO"
        "BITAGAP BIOGRAPHY*RELATED_BIOCLASS<SECRETÁRIO"
        "BITAGAP BIOGRAPHY*RELATED_BIOCLASS<CONSELHEIRA"
        "BITAGAP BIOGRAPHY*RELATED_BIOCLASS<CONSELHEIRO"
        "BITAGAP BIOGRAPHY*RELATED_BIOCLASSCONF"
        "BITAGAP BIOGRAPHY*RELATED_BIOCLASSCONF"
        "BITAGAP BIOGRAPHY*RELATED_BIOCLASSPREG"
        ],
      "BITECA": [
      "BITECA BIOGRAPHY*RELATED_BIOCLASS*<EXECUTOR",
      "BITECA BIOGRAPHY*RELATED_BIOCLASS*<CANCELLER",
      "BITECA BIOGRAPHY*RELATED_BIOCLASS*<CAPITÀ",
      "BITECA BIOGRAPHY*RELATED_BIOCLASS*<ESCRIVÀ",
      "BITECA BIOGRAPHY*RELATED_BIOCLASS*<CRONISTA",
      "BITECA BIOGRAPHY*RELATED_BIOCLASS*<LADY-IN-WAITING",
      "BITECA BIOGRAPHY*RELATED_BIOCLASS*<AMBAIXADOR",
      "BITECA BIOGRAPHY*RELATED_BIOCLASS*<FALCONER",
      "BITECA BIOGRAPHY*RELATED_BIOCLASS*<HERALD",
      "BITECA BIOGRAPHY*RELATED_BIOCLASS*<AMANT",
      "BITECA BIOGRAPHY*RELATED_BIOCLASS*<NOTARI",
      "BITECA BIOGRAPHY*RELATED_BIOCLASS*<OFICIAL",
      "BITECA BIOGRAPHY*RELATED_BIOCLASS*<PARTISAN",
      "BITECA BIOGRAPHY*RELATED_BIOCLASS*<PARTISAN",
      "BITECA BIOGRAPHY*RELATED_BIOCLASS*<REID’ARMES",
      "BITECA BIOGRAPHY*RELATED_BIOCLASS*<ESCRIVÀ",
      "BITECA BIOGRAPHY*RELATED_BIOCLASS*<SECRETARI",
      "BITECA BIOGRAPHY*RELATED_BIOCLASS*CONSELLERA",
      "BITECA BIOGRAPHY*RELATED_BIOCLASS*CONSELLER",
      "BITECA BIOGRAPHY*RELATED_BIOCLASS*APPRENTICE",
      "BITECA UNIFORM_TITLE*RELATED_BIOCLASS*COMENTADOR",
      "BITECA BIOGRAPHY*RELATED_BIOCLASS*PREDICADOR",
      "BITECA BIOGRAPHY*RELATED_BIOCLASS*SUBORDINATE"
      ],
  }

    bib_name = str(self.top_level_bib).split('.')[-1]

    self.single_property_columns = {}

    for category, mappings in SINGLE_PROPERTY_COLUMNS.items():
        if category == "Milestones":
            # Prepend bib_name to all keys in Milestones
            self.single_property_columns[category] = {
                f"{bib_name} {key}": value for key, value in mappings.items()
            }
        elif category == "Related_Bio":
            # Select only the mappings for the current bib_name, if they exist
            if bib_name in mappings:
                self.single_property_columns[category] = mappings[bib_name]
            else:
                self.single_property_columns[category] = {}
        else:
            # For other categories, just copy as-is
            self.single_property_columns[category] = mappings

    related_object_clips = related_object_clips[bib_name]

    subject_object_predicate = lambda row: row['RELATED_BIOCLASS'] in related_object_clips
    df = self.split_column_by_predicate(df, 'RELATED_BIOID', subject_object_predicate,
                                        true_extension='OBJECT', false_extension='SUBJECT')
    # add new columns for the qnumbers using the lookup table if supplied
    df = self.add_qnumber_columns(df, BiographyPreprocessor.TABLE)

    # split single properties columns
    df = self.move_single_property_columns(df, self.single_property_columns, Table.BIOGRAPHY)

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
    df = self.clear_grouped_values_except_first(df, 'BIOID', ['EXPANDED_TITLE_EN'])
    df = self.move_last_column_after(df, 'TITLE_BASIS')
    df['EXPANDED_TITLE_U'] = df.apply (lambda row: self.get_expanded_title(row, dict_geo, self.top_level_bib.language_code()), axis=1)
    df = self.clear_grouped_values_except_first(df, 'BIOID', ['EXPANDED_TITLE_U'])
    df = self.move_last_column_after(df, 'EXPANDED_TITLE_EN')

    # Expanded name is pretty much ok
    df['EXPANDED_NAME'] = df.apply (lambda row: self.get_expanded_name(row), axis=1)

    # truncate any fields that are too long
    df = self.truncate_dataframe(df)

    self.write_result_csv(df, biography_file)
    print(f'{datetime.now()} INFO: done')
