import pandas as pd
from wikibaseintegrator.datatypes import Item, String
from wikibaseintegrator import Qualifiers
import textwrap

from .generic import GenericMapper
from common.wb_manager import PROPERTY_PHILOBIBLON_ID


class MonikerMapper(GenericMapper):
  LABEL_COLUMN = 'MONIKER'

  def read_csv(self, file):
    # TODO special encoding because right now CSVs contains invalids chars (�)
    # self.df = pd.read_csv(file, usecols=[self.ID_COLUMN, self.LABEL_COLUMN], encoding='unicode_escape')
    self.df = pd.read_csv(file, usecols=[self.ID_COLUMN, self.LABEL_COLUMN])

  def get_df_ids(self):
    return self.df[self.ID_COLUMN].unique()

  def get_label(self, df_element):
    return df_element[df_element[self.LABEL_COLUMN].notnull()][self.LABEL_COLUMN]

  def prepare_label(self, pbid, df_element):
    label = self.get_label(df_element)
    if label.empty:
      return None

    label = label.values[0]
    
    # TODO force encoding to utf8 because of problems in charset in CSVs
    # label = label.encode('iso8859-1').decode('utf8')
    # check max length for descriptions in wikibase
    if len(label) > self.MAX_LABEL_CHAR:
      print(f"WARN: trimming description length: '{label}' (PBID={pbid}).")
      label = textwrap.shorten(label, width=self.MAX_LABEL_CHAR, placeholder=" ..")
    return label

  def to_wb_entity(self, pbid, df_element):
    is_new = True
    item = self.wb_manager.get_q_by_pbid(pbid)
    if not item:
      item = self.wb_manager.wbi.item.new()
    else:
      is_new = False

    label = self.prepare_label(pbid, df_element)

    if label:
      item.labels.set(language='es', value=label)
      item.aliases.set(language='es', values=pbid)
      item.claims.add(String(value=pbid, prop_nr=PROPERTY_PHILOBIBLON_ID))
      qualifiers = Qualifiers()
      qualifiers.add(Item(value='Q6', prop_nr='P700'))
      item.claims.add(Item(value='Q4', prop_nr='P131', qualifiers=qualifiers))
      item.claims.add(Item(value='Q5', prop_nr='P17'))
      
      return item, is_new
    else:
      raise ValueError(f'ERROR: null label, ignoring item (PBID={pbid}).')


class InstitutionMonikerMapper(MonikerMapper):
  ID_COLUMN = 'INSID'


class GeographyMonikerMapper(MonikerMapper):
  ID_COLUMN = 'GEOID'


class BibliographyMonikerMapper(MonikerMapper):
  ID_COLUMN = 'BIBID'


class MsEdMonikerMapper(MonikerMapper):
  ID_COLUMN = 'MANID'

  def read_csv(self, file):
    # TODO
    # self.df = pd.read_csv(file, usecols=[self.ID_COLUMN, self.LABEL_COLUMN], encoding='ISO-8859-1')
    self.df = pd.read_csv(file, usecols=[self.ID_COLUMN, self.LABEL_COLUMN])


class BiographyMonikerMapper(MonikerMapper):
  ID_COLUMN = 'BIOID'


class SubjectMonikerMapper(MonikerMapper):
  ID_COLUMN = 'SUBID'


class LibraryMonikerMapper(MonikerMapper):
  ID_COLUMN = 'LIBID'

  def read_csv(self, file):
    # TODO
    # self.df = pd.read_csv(file, usecols=[self.ID_COLUMN, self.LABEL_COLUMN], encoding='ISO-8859-1')
    self.df = pd.read_csv(file, usecols=[self.ID_COLUMN, self.LABEL_COLUMN])


class UniformTitleMonikerMapper(MonikerMapper):
  ID_COLUMN = 'TEXID'


class AnalyticMonikerMapper(MonikerMapper):
  ID_COLUMN = 'CNUM'

  def read_csv(self, file):
    # TODO
    # self.df = pd.read_csv(file, usecols=[self.ID_COLUMN, self.LABEL_COLUMN], encoding='ISO-8859-1')
    self.df = pd.read_csv(file, usecols=[self.ID_COLUMN, self.LABEL_COLUMN])


class CopiesMonikerMapper(MonikerMapper):
  ID_COLUMN = 'COPID'
