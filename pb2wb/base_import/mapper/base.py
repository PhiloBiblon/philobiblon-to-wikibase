from wikibaseintegrator.datatypes import String
import pandas as pd
import math

from .generic import GenericMapper
from common.wb_manager import PROPERTY_PHILOBIBLON_ID


class BaseMapper(GenericMapper):

  def read_csv(self, file):
    # TODO special encoding because right now CSVs contains invalids chars (�)
    # self.df = pd.read_csv(file, usecols=[self.ID_COLUMN, self.LABEL_COLUMN] + ([self.DESC_COLUMN] if self.DESC_COLUMN else []) + self.get_select_extra_cols(), encoding='unicode_escape')
    self.df = pd.read_csv(file, usecols=[self.ID_COLUMN, self.LABEL_COLUMN] + ([self.DESC_COLUMN] if self.DESC_COLUMN else []) + self.get_select_extra_cols())

  def get_df_ids(self):
    return self.df[self.ID_COLUMN].unique()

  def get_cell_value(self, row, column_name):
    if row is not None and column_name:
      cell = row[column_name]
      if not cell.empty:
        if len(cell.index) > 1:
          print(f'WARN: multiple value for {column_name}, getting first value.')
          cell = cell.head(1)
        value = cell.values[0]
        if isinstance(value, str):
          return value
    print(f'WARN: no value found for {column_name}')
    return None

  def get_select_extra_cols(self):
    return []

  def get_label(self, df_element):
    return df_element[df_element[self.LABEL_COLUMN].notnull()][self.LABEL_COLUMN]

  def get_description(self, df_element):
    return df_element[df_element[self.DESC_COLUMN].notnull()][self.DESC_COLUMN]

  def prepare_description(self, pbid, df_element):
    desc = self.get_description(df_element)
    
    if desc is not None and not isinstance(desc, str):
      if desc.empty:
        print(f'WARN: description not found (PBID={pbid}).')
        return None
      elif len(desc.index) > 1:
        print(f"WARN: more than one possible description, taking the first one (PBID={pbid}).")
        desc = desc.head(1)
      desc = desc.values[0]

    if not desc or desc != desc:
      print(f'WARN: null description (PBID={pbid}).')
      return None

    # TODO force encoding to utf8 because of problems in charset in CSVs
    # desc = desc.encode('iso8859-1').decode('utf8')
    # check max length for descriptions in wikibase
    if len(desc) > self.MAX_LABEL_CHAR:
      print(f"WARN: trimming description length: '{desc}' (PBID={pbid}).")
      desc = desc[:self.MAX_LABEL_CHAR]
    return desc

  def prepare_label(self, pbid, df_element):
    label = self.get_label(df_element)

    if label is not None and not isinstance(label, str):
      if label.empty:
        raise ValueError(f'ERROR: label not found (PBID={pbid}).')
      elif len(label.index) > 1:
        print(f"WARN: more than one possible label, taking the first one (PBID={pbid}).")
        label = label.head(1)
      label = label.values[0]

    if not label or label != label:
      raise ValueError(f'ERROR: null label, ignoring item (PBID={pbid}).')

    # TODO force encoding to utf8 because of problems in charset in CSVs
    # label = label.encode('iso8859-1').decode('utf8')
    # check max length for labels in wikibase
    if len(label) > self.MAX_LABEL_CHAR:
      print(f"WARN: trimming label length: '{label}' (PBID={pbid}).")
      label = label[:self.MAX_LABEL_CHAR]
    return label

  def to_wb_entity(self, pbid, df_element):
    label = self.prepare_label(pbid, df_element)

    is_new = True
    item = self.wb_manager.get_q_by_pbid(pbid)
    if not item:
      item = self.wb_manager.wbi.item.new()
    else:
      is_new = False

    desc = self.prepare_description(pbid, df_element)
    if desc and desc == label:
      print(f"WARN: ignored description because have the same value as label (PBID={pbid}).")

    item.labels.set(language='en', value=label)
    if desc and desc != label:
      item.descriptions.set(language='en', value=desc)
    item.aliases.set(language='en', values=pbid)
    item.claims.add(String(value=pbid, prop_nr=PROPERTY_PHILOBIBLON_ID))

    return item, is_new


class InstitutionBaseMapper(BaseMapper):
  ID_COLUMN = 'INSID'
  LABEL_COLUMN = 'MONIKER'
  DESC_COLUMN = 'TYPE'


class GeographyBaseMapper(BaseMapper):
  ID_COLUMN = 'GEOID'
  LABEL_COLUMN = 'NAME'
  DESC_COLUMN = 'TYPE'

  def get_label(self, df_element):
    return df_element[df_element['NAME_CLASS']=='actual'][self.LABEL_COLUMN]

  def get_select_extra_cols(self):
      return ['NAME_CLASS']


class BibliographyBaseMapper(BaseMapper):
  ID_COLUMN = 'BIBID'
  LABEL_COLUMN = 'TITLE'
  DESC_COLUMN = 'MONIKER'

  def get_select_extra_cols(self):
      return ['CREATOR_FNAME', 'CREATOR_LNAME', 'CREATOR_CNAME', 'CREATOR_ROLE']

  def get_label(self, df_element):
    label = None
    
    row = df_element[df_element['CREATOR_ROLE']=='autor']
    if row.empty:
      raise ValueError('ERROR: not found role autor.')
    strings = [row['CREATOR_FNAME'], row['CREATOR_LNAME'], row['CREATOR_CNAME']]
    author = ' '.join(x.values[0] for x in strings if isinstance(x.values[0], str) or not math.isnan(x))
    if author:
      label = author

    row = df_element[df_element['TITLE'].notnull()]
    title = self.get_cell_value(row, 'TITLE')
    if title:
      if label:
        label = label + ', ' + title
      else:
        label = title

    return label


class MsEdBaseMapper(BaseMapper):
  ID_COLUMN = 'MANID'
  LABEL_COLUMN = 'MONIKER'
  DESC_COLUMN = 'MONIKER'

  def read_csv(self, file):
    # TODO
    # df = pd.read_csv(file, usecols=[self.ID_COLUMN, self.LABEL_COLUMN], encoding="iso8859-1")
    df = pd.read_csv(file, usecols=[self.ID_COLUMN, self.LABEL_COLUMN])
    self.df = df[df.MANID.apply(lambda x: isinstance(x, int))]


class BiographyBaseMapper(BaseMapper):
  ID_COLUMN = 'BIOID'
  LABEL_COLUMN = 'NAME_FIRST'
  DESC_COLUMN = 'MONIKER'

  def get_select_extra_cols(self):
      return ['NAME_CLASS', 'NAME_FIRST', 'NAME_LAST', 'NAME_NUMBER', 'NAME_HONORIFIC', 'NAME_EPITHET']

  def get_label(self, df_element):
    row = df_element[df_element['NAME_CLASS']=='nativo']
    if row.empty:
      raise ValueError('ERROR: not found class nativo.')
    if len(row.index) > 1:
      print(f"WARN: more than one possible label, taking the first one (PBID={row[self.ID_COLUMN]}).")
      row = row.head(1)
    strings = [row['NAME_FIRST'], row['NAME_LAST'], row['NAME_NUMBER'], row['NAME_HONORIFIC'], row['NAME_EPITHET']]
    return ' '.join(x.values[0] for x in strings if isinstance(x.values[0], str) or not math.isnan(x))


class SubjectBaseMapper(BaseMapper):
  ID_COLUMN = 'SUBID'
  LABEL_COLUMN = 'HEADING_MAIN'
  DESC_COLUMN = 'HEADING_VARIANT'

  def get_label(self, df_element):
    return df_element[df_element[self.LABEL_COLUMN].notnull()][self.LABEL_COLUMN]

  def get_description(self, df_element):
    heading_variants = df_element[self.DESC_COLUMN].tolist()
    return ', '.join(x for x in heading_variants if isinstance(x, str) or not math.isnan(x))


class LibraryBaseMapper(BaseMapper):
  ID_COLUMN = 'LIBID'
  LABEL_COLUMN = 'NAME'
  DESC_COLUMN = 'MONIKER'

  def get_label(self, df_element):
    return df_element[df_element['NAME_CLASS']=='Actual'][self.LABEL_COLUMN]

  def get_select_extra_cols(self):
      return ['NAME_CLASS']

  def read_csv(self, file):
    # TODO
    # self.df = pd.read_csv(file, usecols=[self.ID_COLUMN, self.LABEL_COLUMN] + ([self.DESC_COLUMN] if self.DESC_COLUMN else []) + self.get_select_extra_cols(), encoding='ISO-8859-1')
    self.df = pd.read_csv(file, usecols=[self.ID_COLUMN, self.LABEL_COLUMN] + ([self.DESC_COLUMN] if self.DESC_COLUMN else []) + self.get_select_extra_cols())


class UniformTitleBaseMapper(BaseMapper):
  ID_COLUMN = 'TEXID'
  LABEL_COLUMN = 'MONIKER'
  DESC_COLUMN = 'CLASS'

  def get_select_extra_cols(self):
      return ['CLASS', 'TYPE']

  def get_description(self, df_element):
    row = df_element[df_element[self.LABEL_COLUMN].notnull()]
    class_field = self.get_cell_value(row, 'CLASS')
    type_field = self.get_cell_value(row, 'TYPE')
    desc = None
    if class_field:
      desc = class_field
    if type_field:
      if desc:
        desc = desc + ', ' + type_field
      else:
        desc = type_field
    return desc


class AnalyticBaseMapper(BaseMapper):
  ID_COLUMN = 'CNUM'
  LABEL_COLUMN = 'MONIKER'
  DESC_COLUMN = 'MONIKER'

  def read_csv(self, file):
    # TODO
    # self.df = pd.read_csv(file, usecols=[self.ID_COLUMN, self.LABEL_COLUMN] + ([self.DESC_COLUMN] if self.DESC_COLUMN else []) + self.get_select_extra_cols(), encoding='ISO-8859-1')
    self.df = pd.read_csv(file, usecols=[self.ID_COLUMN, self.LABEL_COLUMN] + ([self.DESC_COLUMN] if self.DESC_COLUMN else []) + self.get_select_extra_cols())


class CopiesBaseMapper(BaseMapper):
  ID_COLUMN = 'COPID'
  LABEL_COLUMN = 'MONIKER'
  DESC_COLUMN = None
