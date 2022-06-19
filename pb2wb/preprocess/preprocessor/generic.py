import os
import shutil
import re
import textwrap

class GenericPreprocessor:

  def get_format_str(self, format_str, value):
    if value:
      return format_str.format(value = value)
    return ''

  def move_last_column_to(self, df, index):
    col = df.columns.tolist()
    col.insert(index, col.pop())
    return df[col]

  def get_column_index(self, df, column_name):
    return df.columns.get_loc(column_name)

  def check_rows_empty_class(self, df, class_column):
    prefix_columns = class_column[:len(class_column)-6]
    r = re.compile(f'{prefix_columns}.*')

    condition = f'{class_column}.str.len()==0 & (' + ' | '.join([ f'{col_to_check}.str.len()>0' for col_to_check in list(filter(r.match, df.columns))]) + ')'
    check_result = df.query(condition)
    if len(check_result) > 0:
      print(f'WARNING: Class column {class_column} empty but with data in {len(check_result)} rows:')
      print(f"   {check_result['INSID'].tolist()}")
      return True
    return False

  def check_rows_empty_classes(self, df, columns_to_check = None):
    if not columns_to_check:
      r = re.compile('..*CLASS')
      columns_to_check = list(filter(r.match, df.columns))
    for class_column in columns_to_check:
      self.check_rows_empty_class(df, class_column)
    return False

  def set_column_value_by_condition(self, df, condition, column_name, value):
    df.loc[df.eval(condition), column_name] = value

  def add_new_column_by_condition(self, df, condition, new_column_name, value, after_column_name):
    df.loc[df.eval(condition), new_column_name] = value
    return self.move_last_column_to(df, self.get_column_index(df, after_column_name) + 1)

  def add_new_column_from_another(self, df, existing_column_name, new_column_name):
    df[new_column_name] = df[existing_column_name]
    return self.move_last_column_to(df, self.get_column_index(df, existing_column_name) + 1)

  def get_from_value(self, from_value, from_column_value, value, format_str = None):
    if from_column_value == from_value:
      if format_str:
        return self.get_format_str(format_str, value)
      else:
        return value
    else:
      return None

  def add_new_column_from_value(self, df, from_column_name, from_value, new_column_name, column_name_value, format_str = None, after_column_name = None):
    df[new_column_name] = df.apply(lambda row: self.get_from_value(from_value, row[from_column_name], row[column_name_value], format_str), axis=1)
    if after_column_name:
      return self.move_last_column_to(df, self.get_column_index(df, after_column_name) + 1)
    else:
      return self.move_last_column_to(df, self.get_column_index(df, from_column_name) + 1)

  def split_str_column_by_size(self, df, column_name, max_size):
    max_lines = 0
    for index, row in df.iterrows():
      value = row[column_name]
      if value and len(value) > max_size:
        lines = textwrap.wrap(value, max_size, break_long_words=False)
        max_lines = max(max_lines, len(lines))
        df.at[index, column_name] = lines[0]
        for num, line in enumerate(lines[1:]):
          df.at[index, column_name + str(num + 1)] = line
    while max_lines > 1:
      df = self.move_last_column_to(df, self.get_column_index(df, column_name) + 1)
      max_lines -= 1
    return df

  def preprocess(self, file, processed_dir):
    shutil.copyfile(file, os.path.join(processed_dir, os.path.basename(file)))
