import os
import base_import.mapper.moniker as mapper
from common.wb_manager import WBManager
from common.settings import CLEAN_DIR


def get_full_input_path(file):
  return os.path.join(CLEAN_DIR, file)

def base_import():
  print('Preparing wikibase connection ...')
  wb_manager = WBManager()

  print('Migrating analytic ...')
  mapper.AnalyticMonikerMapper(wb_manager).migrate(get_full_input_path('BETA/csvs/beta_analytic.csv'))

  print('Migrating bibliography ...')
  mapper.BibliographyMonikerMapper(wb_manager).migrate(get_full_input_path('BETA/csvs/beta_bibliography.csv'))

  print('Migrating biography ...')
  mapper.BiographyMonikerMapper(wb_manager).migrate(get_full_input_path('BETA/csvs/beta_biography.csv'))

  print('Migrating copies ...')
  mapper.CopiesMonikerMapper(wb_manager).migrate(get_full_input_path('BETA/csvs/beta_copies.csv'))

  print('Migrating geography ...')
  mapper.GeographyMonikerMapper(wb_manager).migrate(get_full_input_path('BETA/csvs/beta_geography.csv'))

  print('Migrating institution ...')
  mapper.InstitutionMonikerMapper(wb_manager).migrate(get_full_input_path('BETA/csvs/beta_institutions.csv'))

  print('Migrating library ...')
  mapper.LibraryMonikerMapper(wb_manager).migrate(get_full_input_path('BETA/csvs/beta_library.csv'))

  print('Migrating ms/ed ...')
  mapper.MsEdMonikerMapper(wb_manager).migrate(get_full_input_path('BETA/csvs/beta_ms_ed.csv'))

  print('Migrating subject ...')
  mapper.SubjectMonikerMapper(wb_manager).migrate(get_full_input_path('BETA/csvs/beta_subject.csv'))

  print('Migrating uniform title ...')
  mapper.UniformTitleMonikerMapper(wb_manager).migrate(get_full_input_path('BETA/csvs/beta_uniform_title.csv'))

  print('done.')
