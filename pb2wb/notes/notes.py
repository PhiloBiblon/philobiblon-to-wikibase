import os
import pandas as pd
from wikibaseintegrator.datatypes import URL
from common.settings import CLEAN_DIR
from common.enums import Table
from common.wi_manager import site
import pywikibot
from common.wb_manager import WBManager, PROPERTY_NOTES

def get_full_input_path(file):
  return os.path.join(CLEAN_DIR, file)

def add_notes(table):
  print('Preparing wikibase connection ...')
  wb_manager = WBManager()

  if table is None or table is Table.ANALYTIC:
    add_notes_to_talk_page(get_full_input_path('BETA/beta_analytic.csv'), wb_manager)
  if table is None or table is Table.BIBLIOGRAPHY:
    add_notes_to_talk_page(get_full_input_path('BETA/beta_bibliography.csv'), wb_manager)
  if table is None or table is Table.BIOGRAPHY:
    add_notes_to_talk_page(get_full_input_path('BETA/beta_biography.csv'), wb_manager)
  if table is None or table is Table.COPIES:
    add_notes_to_talk_page(get_full_input_path('BETA/beta_copies.csv'), wb_manager)
  if table is None or table is Table.GEOGRAPHY:
    add_notes_to_talk_page(get_full_input_path('BETA/beta_geography.csv'), wb_manager)
  if table is None or table is Table.INSTITUTIONS:
    add_notes_to_talk_page(get_full_input_path('BETA/beta_institutions.csv'), wb_manager)
  if table is None or table is Table.LIBRARY:
    add_notes_to_talk_page(get_full_input_path('BETA/beta_library.csv'), wb_manager)
  if table is None or table is Table.MS_ED:
    add_notes_to_talk_page(get_full_input_path('BETA/beta_ms_ed.csv'), wb_manager)
  if table is None or table is Table.SUBJECT:
    add_notes_to_talk_page(get_full_input_path('BETA/beta_subject.csv'), wb_manager)
  if table is None or table is Table.UNIFORM_TITLE:
    add_notes_to_talk_page(get_full_input_path('BETA/beta_uniform_title.csv'), wb_manager)

def add_notes_to_talk_page(filepath, wb_manager):
  print(f'INFO: Processing {filepath} ..')
  df = pd.read_csv(filepath, dtype=str, keep_default_na=False)
  for _, row in df.iterrows():
    if not pd.isnull(row['NOTES']) and not row['NOTES'] == '':
      q_item = wb_manager.get_q_by_pbid(row[0])
      if q_item:
        print(f"Adding notes for {row[0]} into {q_item.id} talk page..") # -{row['NOTES']}-")
        page = add_notes_to_talk_page_item(q_item.id, row['NOTES'])
        add_notes_property_to_item(q_item, page)
      else:
        print(f"ERROR: Not found Q item for {row[0]}, notes are ignored.")


def add_notes_to_talk_page_item(q_number, notes):
  page = pywikibot.Page(site, f'Item_talk:{q_number}')
  page.text = notes
  page.save('Added PhiloBiblon notes')
  return page

def add_notes_property_to_item(q_item, page):
  q_item.claims.add(URL(value=page.full_url(), prop_nr=PROPERTY_NOTES))
  q_item.write()
