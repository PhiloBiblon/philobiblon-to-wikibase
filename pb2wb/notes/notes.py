import os
import pandas as pd
from wikibaseintegrator.datatypes import URL
from common.settings import CLEAN_DIR
from common.enums import Table
from common.wi_manager import site
import pywikibot
from common.wb_manager import WBManager, PROPERTY_NOTES
from common.settings import TEMP_DICT

reset = TEMP_DICT['RESET']

def get_full_input_path(file):
  return os.path.join(CLEAN_DIR, file)

def add_notes(table, bib):
  print('Preparing wikibase connection ...')
  wb_manager = WBManager()
  print(f'Processing notes for {bib}')
  if table is None or table is Table.ANALYTIC:
    add_notes_to_talk_page(get_full_input_path(f'{bib}/csvs/{bib.lower()}_analytic.csv'), wb_manager)
  if table is None or table is Table.BIBLIOGRAPHY:
    add_notes_to_talk_page(get_full_input_path(f'{bib}/csvs/{bib.lower()}_bibliography.csv'), wb_manager)
  if table is None or table is Table.BIOGRAPHY:
    add_notes_to_talk_page(get_full_input_path(f'{bib}/csvs/{bib.lower()}_biography.csv'), wb_manager)
  if table is None or table is Table.COPIES:
    add_notes_to_talk_page(get_full_input_path(f'{bib}/csvs/{bib.lower()}_copies.csv'), wb_manager)
  if table is None or table is Table.GEOGRAPHY:
    add_notes_to_talk_page(get_full_input_path(f'{bib}/csvs/{bib.lower()}_geography.csv'), wb_manager)
  if table is None or table is Table.INSTITUTIONS:
    add_notes_to_talk_page(get_full_input_path(f'{bib}/csvs/{bib.lower()}_institutions.csv'), wb_manager)
  if table is None or table is Table.LIBRARY:
    add_notes_to_talk_page(get_full_input_path(f'{bib}/csvs/{bib.lower()}_library.csv'), wb_manager)
  if table is None or table is Table.MS_ED:
    add_notes_to_talk_page(get_full_input_path(f'{bib}/csvs/{bib.lower()}_ms_ed.csv'), wb_manager)
  if table is None or table is Table.SUBJECT:
    add_notes_to_talk_page(get_full_input_path(f'{bib}/csvs/{bib.lower()}_subject.csv'), wb_manager)
  if table is None or table is Table.UNIFORM_TITLE:
    add_notes_to_talk_page(get_full_input_path(f'{bib}/csvs/{bib.lower()}_uniform_title.csv'), wb_manager)

def add_notes_to_talk_page(filepath, wb_manager):
  print(f'INFO: Processing {filepath} ..')
  df = pd.read_csv(filepath, dtype=str, keep_default_na=False)
  for _, row in df.iterrows():
    if not pd.isnull(row['NOTES']) and not row['NOTES'] == '':
      q_item = wb_manager.get_q_by_pbid(row[0])
      if q_item:
        if reset:
          print(f"Resetting notes for {row[0]}")
          reset_talk_page_notes(q_item.id)
        else:
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

def reset_talk_page_notes(q_number):
    page = pywikibot.Page(site, f'Item_talk:{q_number}')
    if page.text.strip():  # Check for existing content
        page.text = ""  # Zero out the talk page
        page.save('Reset Item_talk page to empty')
    else:
        print("Talk page is already empty.")
    return page
