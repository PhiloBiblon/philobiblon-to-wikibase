import pandas as pd
from wikibaseintegrator.datatypes import Item, String
from common.wb_manager import WBManager, PROPERTY_INSTANCE_OF, PROPERTY_PHILOBIBLON_ID

GROUP = 'BETA'

def create_p_dataclip(label, pbid):
  p_item = wb_manager.create_wb_p(label, 'en', 'wikibase-item')
  p_item.claims.add(String(value=pbid, prop_nr=PROPERTY_PHILOBIBLON_ID))
  p_item.write()
  return p_item


def get_or_create_p_dataclip(dataclipname, table):
  pbid = GROUP + '-' + table + '/' + dataclipname
  p_dataclip = wb_manager.get_p_by_pbid(pbid)
  if p_dataclip:
    return p_dataclip, False
  label = pbid
  p_dataclip = create_p_dataclip(label, pbid)
  return p_dataclip, True


def create_q_dataclip(label, pbid):
  q_item = wb_manager.create_wb_q(label, 'en')
  q_item.claims.add(String(value=pbid, prop_nr=PROPERTY_PHILOBIBLON_ID))
  q_item.write()
  return q_item


def get_or_create_q_dataclip(dataclipname, table):
  pbid = GROUP + '-' + table + '/' + dataclipname
  q_dataclip = wb_manager.get_q_by_pbid(pbid)
  if q_dataclip:
    return q_dataclip, False
  label = pbid
  q_dataclip = create_q_dataclip(label, pbid)
  return q_dataclip, True


def create_q_value(value, q_dataclip):
  q_item = wb_manager.wbi.item.new()
  q_item.labels.set(language='en', value=value)
  q_item.claims.add(Item(value=q_dataclip.id, prop_nr=PROPERTY_INSTANCE_OF))
  q_item.write()
  return q_item


def get_or_create_q_value(value, q_dataclip):
  q_value = wb_manager.get_by_dataclipvalue(value, q_dataclip)
  if q_value:
    return q_value, False
  q_value = create_q_value(value, q_dataclip)
  return q_value, True


print('Preparing wikibase connection ...')
wb_manager = WBManager()

file = 'data/BETA - DataClips.CSV'

print(f'Reading dataclips CSV file {file} ...')
df = pd.read_csv(file)

print('Importing dataclips ...')
for table in df['TABLE'].unique():
  print(f"Importing table {table} ..")
  for dataclip in df[df['TABLE']==table]['DATACLIP'].unique():
    p_dataclip, is_new_p = get_or_create_p_dataclip(dataclip, table)
    q_dataclip, is_new_q = get_or_create_q_dataclip(dataclip, table)
    print(f"Dataclip {table}/{dataclip} mapped with {'new' if is_new_p else 'existing'} P item {p_dataclip.id} and {'new' if is_new_q else 'existing'} Q item {q_dataclip.id}")
    for _, row in df[(df['TABLE']==table) & (df['DATACLIP']==dataclip)].iterrows():
      value = row['REVEAL']
      q_value, is_new = get_or_create_q_value(value, q_dataclip)
      print(f"Dataclip value {table}/{dataclip}/{value} mapped with {'new' if is_new else 'existing'} Q item {q_value.id}")

print('done.')