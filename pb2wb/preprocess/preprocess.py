import os
from .preprocessor.generic import GenericPreprocessor
from .preprocessor.biography import BiographyPreprocessor
from .preprocessor.institution import InstitutionPreprocessor
from common.settings import CLEAN_DIR, PROCESSED_DIR
from common.enums import Table

def get_full_path(file):
  return os.path.join(CLEAN_DIR, file)

def preprocess(table):
  beta_processed_dir = os.path.join(PROCESSED_DIR, 'BETA')
  os.makedirs(beta_processed_dir, exist_ok=False)

  if table and table is Table.ANALYTIC:
    GenericPreprocessor().preprocess(get_full_path('BETA/beta_analytic.csv'), beta_processed_dir)
  if table and table is Table.BIBLIOGRAPHY:
    GenericPreprocessor().preprocess(get_full_path('BETA/beta_bibliography.csv'), beta_processed_dir)
  if table and table is Table.BIOGRAPHY:
    BiographyPreprocessor().preprocess(get_full_path('BETA/beta_biography.csv'), get_full_path('BETA/beta_geography.csv'), beta_processed_dir)
  if table and table is Table.COPIES:
    GenericPreprocessor().preprocess(get_full_path('BETA/beta_copies.csv'), beta_processed_dir)
  if table and table is Table.GEOGRAPHY:
    GenericPreprocessor().preprocess(get_full_path('BETA/beta_geography.csv'), beta_processed_dir)
  if table and table is Table.INSTITUTIONS:
    InstitutionPreprocessor().preprocess(get_full_path('BETA/beta_institutions.csv'), beta_processed_dir)
  if table and table is Table.LIBRARY:
    GenericPreprocessor().preprocess(get_full_path('BETA/beta_library.csv'), beta_processed_dir)
  if table and table is Table.MS_ED:
    GenericPreprocessor().preprocess(get_full_path('BETA/beta_ms_ed.csv'), beta_processed_dir)
  if table and table is Table.SUBJECT:
    GenericPreprocessor().preprocess(get_full_path('BETA/beta_subject.csv'), beta_processed_dir)
  if table and table is Table.UNIFORM_TITLE:
    GenericPreprocessor().preprocess(get_full_path('BETA/beta_uniform_title.csv'), beta_processed_dir)
