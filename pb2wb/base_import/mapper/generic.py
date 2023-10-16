import traceback
import sys
import time


class GenericMapper:
  MAX_LABEL_CHAR = 250
  NUM_WRITE_ATTEMPTS = 5

  def __init__(self, wb_manager):
    self.wb_manager = wb_manager

  def get_pbid(self, id):
    return id

  def read_csv(self, file):
    raise NotImplementedError

  def to_wb_entity(self, pbid, df_element):
    raise NotImplementedError

  def update_wb(self):
    for id in self.get_df_ids():
      pbid = self.get_pbid(id)
      df_element = self.df[self.df[self.ID_COLUMN]==id]
      updated = self.update_wb_element(pbid, df_element)

  def update_wb_element(self, pbid, df_element):
      num_attempts = self.NUM_WRITE_ATTEMPTS
      updated = False
      while not updated and num_attempts > 0:
        try:
          item, is_new = self.to_wb_entity(pbid, df_element)
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
              print(f'WARN: {repr(e)}, write item failed (PBID={pbid}), trying again (pending attempts {num_attempts})')

  def migrate(self, file):
    self.read_csv(file)
    self.update_wb()
