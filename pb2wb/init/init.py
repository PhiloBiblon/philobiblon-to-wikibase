import pandas as pd
from wikibaseintegrator.datatypes import String
from common.wb_manager import PROPERTY_PHILOBIBLON_ID, WBManager


MAP_PROPS_FILE = 'init/conf/p_properties.csv'
MAP_ITEMS_FILE = 'init/conf/q_items.csv'

def get_p_numeric(p_number):
  return int(p_number[1:])

def get_last_p_number(wb_manager):
    last_p = wb_manager.get_last_p()
    if last_p:
      return last_p.id
    else:
      return None

def create_wb_p_safely(wb_manager, p_number, label, lang, type, last_p_number):
  if not type and last_p_number and get_p_numeric(p_number) <= get_p_numeric(last_p_number):
    print(f"WARN: Ignoring property {p_number} without type...")
    return None

  # p_number == p_number is to check that is not NaN
  if p_number and p_number == p_number:
    p_item = wb_manager.get_wb_p(p_number)
    if p_item:
      if p_item.datatype == type:
        if p_item.labels.get(lang) == label:
          print(f'INFO: P property {p_number} already exists and is OK.')
        else:
          print(f"INFO: P property {p_number} updating label from '{p_item.labels.get(lang)}' to '{label}'.")
          p_item.labels.set(language=lang, value=label)
          p_item.write()
      else:
        raise Exception(f"""ERROR: P property {p_number} already exists with different type!
          (label: existing '{p_item.labels.get(lang)}' vs expected '{label}', type: existing '{p_item.datatype}' vs expected '{type}'""")
    else:
      try:
        p_item = wb_manager.create_wb_p(label, lang, type)
        print(f'INFO: Created new property {p_item.id} with label {p_item.labels.get(lang)} ({lang}) and type {p_item.datatype}.')
      except Exception as err:
        if label:
          print(f'ERROR: Creating property {p_number} with label {label} ({lang}) and type {type}: {err}')
          raise err
        return None
      if not p_item.id == p_number:
        raise ValueError(f'ERROR: New property has not the expected number, current {p_item.id} vs expected {p_number}.')
  else:
    p_item = wb_manager.create_wb_p(label, lang, type)
    print(f'INFO: Created new property {p_item.id} with label {p_item.labels.get(lang)} ({lang}) and type {p_item.datatype}.')

  return p_item


def create_wb_new_q(wb_manager, label, lang, alias, pbid):
  q_item = wb_manager.wbi.item.new()
  q_item.labels.set(language=lang, value=label)
  if alias:
    q_item.aliases.set(language=lang, values=alias)
  if pbid:
    q_item.claims.add(String(value=pbid, prop_nr=PROPERTY_PHILOBIBLON_ID))
  q_item.write()
  return q_item


def is_valid_existing_q(q_item, lang, pbid):
  if pbid:
    aliases = q_item.aliases.get(lang)
    if pbid not in q_item.aliases.get(lang):
      raise Exception(f"""ERROR: Q item {q_item.id} already exists with distinct pbid!
        (pbid: existing '{aliases}' vs expected '{pbid}'""")
  return True


def create_wb_q_safely(wb_manager, q_number, label, lang, alias, pbid):
  if q_number:
    q_item = wb_manager.get_wb_q(q_number)
  elif pbid:
    q_item = wb_manager.get_q_by_pbid(pbid)
  else:
    q_item = wb_manager.get_q_by_label(label, lang)
  if q_item:
    if is_valid_existing_q(q_item, lang, pbid):
      if q_item.labels.get(lang) != label:
          print(f"INFO: Q item {q_item.id} updating label from '{q_item.labels.get(lang)}' to '{label}'.")
          q_item.labels.set(language=lang, value=label)
          q_item.write()
      else:
        print(f'INFO: Q item {q_item.id} already exists and is OK.')
  else:
    q_item = create_wb_new_q(wb_manager, label, lang, alias, pbid)
    print(f'INFO: Created new item {q_item.id} with alias {q_item.aliases.get(lang)} with label {q_item.labels.get(lang)} ({lang}).')
  return q_item


def init(only_properties, only_qitems):
  print('Preparing wikibase connection ...')
  wb_manager = WBManager()
  
  if not only_qitems:
    last_p_number = get_last_p_number(wb_manager)
    print(f'Last existing property {last_p_number}')
    df_props = pd.read_csv(MAP_PROPS_FILE, comment='#')
    df_props = df_props.where(pd.notnull(df_props), None)
    for _, row in df_props.iterrows():
      create_wb_p_safely(wb_manager, row['PNUMBER'], row['LABEL'], row['LANG'], row['TYPE'], last_p_number)

  if not only_properties:
    df_items = pd.read_csv(MAP_ITEMS_FILE, comment='#', keep_default_na=False)
    for _, row in df_items.iterrows():
      create_wb_q_safely(wb_manager, row['QNUMBER'], row['LABEL'], row['LANG'], row['ALIAS'], row['PBID'])

  print('done.')
