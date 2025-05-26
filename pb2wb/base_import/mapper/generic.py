import traceback
import sys
import time
from common.settings import TEMP_DICT


class GenericMapper:
  MAX_LABEL_CHAR = 250
  NUM_WRITE_ATTEMPTS = 5

  def __init__(self, wb_manager):
    self.wb_manager = wb_manager
    self.skip_existing = True
    self.sample_size = 10
    self.DRYRUN = TEMP_DICT['DRYRUN']
    self.resume_id = TEMP_DICT['RESUME_ID']

  def with_skip_existing(self, b: bool):
    self.skip_existing = b
    return self

  def with_dry_run(self, b: bool):
    self.dry_run = b
    return self

  def with_sample_size(self, i: int):
    self.sample_size = i
    return self

  def get_pbid(self, id):
    return id

  def read_csv(self, file):
    raise NotImplementedError

  def to_wb_entity(self, pbid, df_element):
    raise NotImplementedError

  def update_wb(self):
    print(f'{self.sample_size = }')
    for id in self.get_df_ids()[:self.sample_size] if self.sample_size > 0 else self.get_df_ids():
      pbid = self.get_pbid(id)
      if int(pbid.split()[-1]) <= self.resume_id:
        print(f"Skipping item PBID={pbid} mapped with {id}")
        continue
      if self.skip_existing:
        item = self.wb_manager.get_q_by_pbid(pbid)
        if item is not None:
          print(f"Skipping item PBID={pbid} mapped with existing {item.id}")
          continue
      df_element = self.df[self.df[self.ID_COLUMN]==id]
      updated = self.update_wb_element(pbid, df_element)

  def update_wb_element(self, pbid, df_element):
      num_attempts = self.NUM_WRITE_ATTEMPTS
      updated = False
      while not updated and num_attempts > 0:
        try:
          item, is_new = self.to_wb_entity(pbid, df_element)
          if self.DRYRUN:
            print(f"DRYRUN: Stopping before writing item PBID={pbid} mapped with {'new' if is_new else 'existing'} {item.id}")
            break
          item.write()
          print(f"Writing item PBID={pbid} mapped with {'new' if is_new else 'existing'} {item.id}")
          updated = True
        except Exception as e:
          num_attempts = num_attempts - 1
          if 'already has label' in repr(e):
            print(f'ERROR: duplicated label, {repr(e)}, ignoring item (PBID={pbid}).')
            num_attempts = 0
          else:
            if num_attempts == 0:
              print(f'ERROR: {repr(e)}, ignoring item (PBID={pbid}).')
              traceback.print_exc(file=sys.stdout)
              time.sleep(1)
            else:
              print(f'WARN: {repr(e)}, write item failed (PBID={pbid}), trying again in 60 seconds (pending attempts {num_attempts})')
              time.sleep(60)  # Wait for 60 seconds before retrying

  def migrate(self, file):
    self.read_csv(file)
    self.update_wb()
