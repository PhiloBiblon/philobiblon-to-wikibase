import os
from .preprocessor.generic import GenericPreprocessor
from .preprocessor.analytic import AnalyticPreprocessor
from .preprocessor.bibliography import BibliographyPreprocessor
from .preprocessor.biography import BiographyPreprocessor
from .preprocessor.copies import CopiesPreprocessor
from .preprocessor.geography import GeographyPreprocessor
from .preprocessor.institution import InstitutionPreprocessor
from .preprocessor.library import LibraryPreprocessor
from .preprocessor.ms_ed import MsEdPreprocessor
from .preprocessor.subject import SubjectPreprocessor
from .preprocessor.uniform_title import UniformTitlePreprocessor
from common.settings import CLEAN_DIR, PRE_PROCESSED_DIR
from common.enums import Table

def get_full_input_path(file):
  return os.path.join(CLEAN_DIR, file)

def preprocess(table):
  qnumber_lookup_file = get_full_input_path('BETA/lookup.csv')
  if not os.path.isfile(qnumber_lookup_file):
    print(f"No qnumber lookup file found. Looked here:: {qnumber_lookup_file}")
    qnumber_lookup_file = None

  beta_pre_processed_dir = os.path.join(PRE_PROCESSED_DIR, 'BETA')
  os.makedirs(beta_pre_processed_dir, exist_ok=True)

  if table is None or table is Table.ANALYTIC:
    AnalyticPreprocessor().preprocess(get_full_input_path('BETA/csvs/beta_analytic.csv'), beta_pre_processed_dir,
                                      qnumber_lookup_file)
  if table is None or table is Table.BIBLIOGRAPHY:
    BibliographyPreprocessor().preprocess(get_full_input_path('BETA/csvs/beta_bibliography.csv'), beta_pre_processed_dir,
                                     qnumber_lookup_file)
  if table is None or table is Table.BIOGRAPHY:
    BiographyPreprocessor().preprocess(get_full_input_path('BETA/csvs/beta_biography.csv'),
                                       get_full_input_path('BETA/csvs/beta_geography.csv'),
                                       beta_pre_processed_dir,
                                       qnumber_lookup_file)
  if table is None or table is Table.COPIES:
    CopiesPreprocessor().preprocess(get_full_input_path('BETA/csvs/beta_copies.csv'), beta_pre_processed_dir,
                                     qnumber_lookup_file)
  if table is None or table is Table.GEOGRAPHY:
    GeographyPreprocessor().preprocess(get_full_input_path('BETA/csvs/beta_geography.csv'), beta_pre_processed_dir,
                                       qnumber_lookup_file)
  if table is None or table is Table.INSTITUTIONS:
    InstitutionPreprocessor().preprocess(get_full_input_path('BETA/csvs/beta_institutions.csv'),
                                         beta_pre_processed_dir, qnumber_lookup_file)
  if table is None or table is Table.LIBRARY:
    LibraryPreprocessor().preprocess(get_full_input_path('BETA/csvs/beta_library.csv'), beta_pre_processed_dir,
                                     qnumber_lookup_file)
  if table is None or table is Table.MS_ED:
    MsEdPreprocessor().preprocess(get_full_input_path('BETA/csvs/beta_ms_ed.csv'), beta_pre_processed_dir,
                                    qnumber_lookup_file)
  if table is None or table is Table.SUBJECT:
    SubjectPreprocessor().preprocess(get_full_input_path('BETA/csvs/beta_subject.csv'), beta_pre_processed_dir,
                                     qnumber_lookup_file)
  if table is None or table is Table.UNIFORM_TITLE:
    UniformTitlePreprocessor().preprocess(get_full_input_path('BETA/csvs/beta_uniform_title.csv'), beta_pre_processed_dir,
                                     qnumber_lookup_file)
