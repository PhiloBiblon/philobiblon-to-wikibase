import os
from .postprocessor.generic import GenericPostprocessor
from common.settings import OPENREFINE_PROCESSED_DIR, POST_PROCESSED_DIR
from common.enums import Table

def get_full_input_path(file):
  return os.path.join(OPENREFINE_PROCESSED_DIR, file)

def postprocess(table):
  beta_post_processed_dir = os.path.join(POST_PROCESSED_DIR, 'BETA')
  os.makedirs(beta_post_processed_dir, exist_ok=False)

  if table is None or table is Table.ANALYTIC:
    GenericPostprocessor().postprocess(get_full_input_path('BETA/beta_analytic.qs'), beta_post_processed_dir)
  if table is None or table is Table.BIBLIOGRAPHY:
    GenericPostprocessor().postprocess(get_full_input_path('BETA/beta_bibliography.qs'), beta_post_processed_dir)
  if table is None or table is Table.BIOGRAPHY:
    GenericPostprocessor().postprocess(get_full_input_path('BETA/beta_biography.qs'), beta_post_processed_dir)
  if table is None or table is Table.COPIES:
    GenericPostprocessor().postprocess(get_full_input_path('BETA/beta_copies.qs'), beta_post_processed_dir)
  if table is None or table is Table.GEOGRAPHY:
    GenericPostprocessor().postprocess(get_full_input_path('BETA/beta_geography.qs'), beta_post_processed_dir)
  if table is None or table is Table.INSTITUTIONS:
    GenericPostprocessor().postprocess(get_full_input_path('BETA/beta_institutions.qs'), beta_post_processed_dir)
  if table is None or table is Table.LIBRARY:
    GenericPostprocessor().postprocess(get_full_input_path('BETA/beta_library.qs'), beta_post_processed_dir)
  if table is None or table is Table.MS_ED:
    GenericPostprocessor().postprocess(get_full_input_path('BETA/beta_ms_ed.qs'), beta_post_processed_dir)
  if table is None or table is Table.SUBJECT:
    GenericPostprocessor().postprocess(get_full_input_path('BETA/beta_subject.qs'), beta_post_processed_dir)
  if table is None or table is Table.UNIFORM_TITLE:
    GenericPostprocessor().postprocess(get_full_input_path('BETA/beta_uniform_title.qs'), beta_post_processed_dir)
