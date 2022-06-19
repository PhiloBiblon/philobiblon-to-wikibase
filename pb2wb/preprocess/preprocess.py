import os
from .preprocessor.generic import GenericPreprocessor
from .preprocessor.biography import BiographyPreprocessor
from .preprocessor.institution import InstitutionPreprocessor
from common.settings import CLEAN_DIR, PROCESSED_DIR

def get_full_path(file):
  return os.path.join(CLEAN_DIR, file)

def preprocess():
  beta_processed_dir = os.path.join(PROCESSED_DIR, 'BETA')
  os.makedirs(beta_processed_dir, exist_ok=False)

  GenericPreprocessor().preprocess(get_full_path('BETA/beta_analytic.csv'), beta_processed_dir)
  GenericPreprocessor().preprocess(get_full_path('BETA/beta_bibliography.csv'), beta_processed_dir)
  BiographyPreprocessor().preprocess(get_full_path('BETA/beta_biography.csv'), get_full_path('BETA/beta_geography.csv'), beta_processed_dir)
  GenericPreprocessor().preprocess(get_full_path('BETA/beta_copies.csv'), beta_processed_dir)
  GenericPreprocessor().preprocess(get_full_path('BETA/beta_geography.csv'), beta_processed_dir)
  InstitutionPreprocessor().preprocess(get_full_path('BETA/beta_institutions.csv'), beta_processed_dir)
  GenericPreprocessor().preprocess(get_full_path('BETA/beta_library.csv'), beta_processed_dir)
  GenericPreprocessor().preprocess(get_full_path('BETA/beta_ms_ed.csv'), beta_processed_dir)
  GenericPreprocessor().preprocess(get_full_path('BETA/beta_subject.csv'), beta_processed_dir)
  GenericPreprocessor().preprocess(get_full_path('BETA/beta_uniform_title.csv'), beta_processed_dir)
