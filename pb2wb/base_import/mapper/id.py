import pandas as pd
from wikibaseintegrator.datatypes import String

from .generic import GenericMapper
from common.wb_manager import PROPERTY_PHILOBIBLON_ID


class IdMapper(GenericMapper):
  DESC_COLUMN = 'MONIKER'

  def read_csv(self, file):
    # TODO special encoding because right now CSVs contains invalids chars (�)
    # self.df = pd.read_csv(file, usecols=[self.ID_COLUMN, self.DESC_COLUMN], encoding='unicode_escape')
    self.df = pd.read_csv(file, usecols=[self.ID_COLUMN, self.DESC_COLUMN])

  def get_df_ids(self):
    return self.df[self.ID_COLUMN].unique()

  def get_description(self, df_element):
    return df_element[df_element[self.DESC_COLUMN].notnull()][self.DESC_COLUMN]

  def prepare_description(self, pbid, df_element):
    desc = self.get_description(df_element)
    if desc.empty:
      print(f'WARN: description not found (PBID={pbid}).')
      return None

    desc = desc.values[0]
    
    # TODO force encoding to utf8 because of problems in charset in CSVs
    # desc = desc.encode('iso8859-1').decode('utf8')
    # check max length for descriptions in wikibase
    if len(desc) > self.MAX_LABEL_CHAR:
      print(f"WARN: trimming description length: '{desc}' (PBID={pbid}).")
      desc = desc[:self.MAX_LABEL_CHAR]
    return desc

  def to_wb_entity(self, pbid, df_element):
    is_new = True
    item = self.wb_manager.get_q_by_pbid(pbid)
    if not item:
      item = self.wb_manager.wbi.item.new()
    else:
      is_new = False

    desc = self.prepare_description(pbid, df_element)

    item.labels.set(language='en', value=pbid)
    if desc:
      item.descriptions.set(language='en', value=desc)
    item.aliases.set(language='en', values=pbid)
    item.claims.add(String(value=pbid, prop_nr=PROPERTY_PHILOBIBLON_ID))

    return item, is_new


class InstitutionIdMapper(IdMapper):
  ID_COLUMN = 'INSID'


class GeographyIdMapper(IdMapper):
  ID_COLUMN = 'GEOID'


class BibliographyIdMapper(IdMapper):
  ID_COLUMN = 'BIBID'


class MsEdIdMapper(IdMapper):
  ID_COLUMN = 'MANID'

  def read_csv(self, file):
    # TODO
    # self.df = pd.read_csv(file, usecols=[self.ID_COLUMN, self.DESC_COLUMN], encoding='ISO-8859-1')
    self.df = pd.read_csv(file, usecols=[self.ID_COLUMN, self.DESC_COLUMN])


class BiographyIdMapper(IdMapper):
  ID_COLUMN = 'BIOID'


class SubjectIdMapper(IdMapper):
  ID_COLUMN = 'SUBID'


class LibraryIdMapper(IdMapper):
  ID_COLUMN = 'LIBID'

  def read_csv(self, file):
    # TODO
    # self.df = pd.read_csv(file, usecols=[self.ID_COLUMN, self.DESC_COLUMN], encoding='ISO-8859-1')
    self.df = pd.read_csv(file, usecols=[self.ID_COLUMN, self.DESC_COLUMN])


class UniformTitleIdMapper(IdMapper):
  ID_COLUMN = 'TEXID'


class AnalyticIdMapper(IdMapper):
  ID_COLUMN = 'CNUM'

  def read_csv(self, file):
    # TODO
    # self.df = pd.read_csv(file, usecols=[self.ID_COLUMN, self.DESC_COLUMN], encoding='ISO-8859-1')
    self.df = pd.read_csv(file, usecols=[self.ID_COLUMN, self.DESC_COLUMN])


class CopiesIdMapper(IdMapper):
  ID_COLUMN = 'COPID'
