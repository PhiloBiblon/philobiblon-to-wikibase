import os
from .preprocessor.generic import GenericPreprocessor
from .preprocessor.biography import BiographyPreprocessor
from .preprocessor.institution import InstitutionPreprocessor
from common.settings import CLEAN_DIR, PRE_PROCESSED_DIR
from common.enums import Table

def get_full_input_path(file):
  return os.path.join(CLEAN_DIR, file)

def preprocess(table):
  beta_pre_processed_dir = os.path.join(PRE_PROCESSED_DIR, 'BETA')
  os.makedirs(beta_pre_processed_dir, exist_ok=False)

  if table is None or table is Table.ANALYTIC:
    GenericPreprocessor().preprocess(get_full_input_path('BETA/beta_analytic.csv'), beta_pre_processed_dir)
  if table is None or table is Table.BIBLIOGRAPHY:
    GenericPreprocessor().preprocess(get_full_input_path('BETA/beta_bibliography.csv'), beta_pre_processed_dir)
  if table is None or table is Table.BIOGRAPHY:
    BiographyPreprocessor().preprocess(get_full_input_path('BETA/beta_biography.csv'), get_full_input_path('BETA/beta_geography.csv'), beta_pre_processed_dir)
  if table is None or table is Table.COPIES:
    GenericPreprocessor().preprocess(get_full_input_path('BETA/beta_copies.csv'), beta_pre_processed_dir)
  if table is None or table is Table.GEOGRAPHY:
    GenericPreprocessor().preprocess(get_full_input_path('BETA/beta_geography.csv'), beta_pre_processed_dir)
  if table is None or table is Table.INSTITUTIONS:
    InstitutionPreprocessor().preprocess(get_full_input_path('BETA/beta_institutions.csv'), beta_pre_processed_dir)
  if table is None or table is Table.LIBRARY:
    GenericPreprocessor().preprocess(get_full_input_path('BETA/beta_library.csv'), beta_pre_processed_dir)
  if table is None or table is Table.MS_ED:
    GenericPreprocessor().preprocess(get_full_input_path('BETA/beta_ms_ed.csv'), beta_pre_processed_dir)
  if table is None or table is Table.SUBJECT:
    GenericPreprocessor().preprocess(get_full_input_path('BETA/beta_subject.csv'), beta_pre_processed_dir)
  if table is None or table is Table.UNIFORM_TITLE:
    GenericPreprocessor().preprocess(get_full_input_path('BETA/beta_uniform_title.csv'), beta_pre_processed_dir)
