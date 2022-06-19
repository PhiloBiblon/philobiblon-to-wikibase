import traceback


class GenericMapper:
  MAX_LABEL_CHAR = 250

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
      try:
        item, is_new = self.to_wb_entity(pbid, df_element)
        item.write()
      except Exception as e:
        if 'already has label' in repr(e):
          print(f'ERROR: duplicated label, {repr(e)}, ignoring item (PBID={pbid}).')
        else:
          print(f'ERROR: {repr(e)}, ignoring item (PBID={pbid}).')
          traceback.print_exc()
        continue
      print(f"Writing item PBID={pbid} mapped with {'new' if is_new else 'existing'} {item.id}")

  def migrate(self, file):
    self.read_csv(file)
    self.update_wb()
