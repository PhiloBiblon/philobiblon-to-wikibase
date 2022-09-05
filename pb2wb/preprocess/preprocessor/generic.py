import os
import shutil
import re
import textwrap

class GenericPreprocessor:

  def get_format_str(self, format_str, value):
    """
    Applies the format parameter to the value.

    :param format_str: format string
    :param value: value to format
    :return: formatted value
    """ 
    if value:
      return format_str.format(value = value)
    return ''

  def move_last_column_to(self, df, index):
    """
    Move last column in dataframe to the index position.

    :param df: dataframe
    :param index: destination position
    :return: dataframe updated
    """
    col = df.columns.tolist()
    col.insert(index, col.pop())
    return df[col]

  def move_last_column_after(self, df, column_name):
    """
    Move last column in dataframe after column passed as parameter.

    :param df: dataframe
    :param column_name: column name before
    :return: dataframe updated
    """
    return self.move_last_column_to(df, self.get_column_index(df, column_name) + 1)

  def get_column_index(self, df, column_name):
    """
    Get column index in dataframe for the column name.

    :param df: dataframe
    :param column_name: column name to find
    :return: index position
    """
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
    """
    Check that passed columns not contain empty rows.

    :param df: dataframe
    :param column_to_check: list of columns to check
    :return: True if some column contains empty values
    """
    if not columns_to_check:
      r = re.compile('..*CLASS')
      columns_to_check = list(filter(r.match, df.columns))
    for class_column in columns_to_check:
      self.check_rows_empty_class(df, class_column)
    return False

  def set_column_value_by_condition(self, df, condition, column_name, value):
    """
    Sets the value to the column's rows that matches the condition.

    :param df: dataframe
    :param condition: condition to filter the rows
    :param column_name: column to update
    :param value: value to set
    """
    df.loc[df.eval(condition), column_name] = value

  def add_new_column_by_condition(self, df, condition, new_column_name, value):
    """
    Sets the value to the column's rows that matches the condition.

    :param df: dataframe
    :param condition: condition to filter the rows
    :param column_name: column to update
    :param value: value to set
    :return dataframe updated
    """
    df.loc[df.eval(condition), new_column_name] = value
    return df

  def add_new_column(self, df, new_column_name, defaul_value):
    """
    Creates a new column using a default value.

    :param df: dataframe
    :param existing_column_name: existing column
    :param new_column_name: new column name
    :return dataframe updated
    """
    df[new_column_name] = defaul_value
    return df

  def add_new_column_from_another(self, df, existing_column_name, new_column_name):
    """
    Creates a copy of an existing column.

    :param df: dataframe
    :param existing_column_name: existing column
    :param new_column_name: new column name
    :return dataframe updated
    """
    df[new_column_name] = df[existing_column_name]
    return df

  def get_from_value(self, from_value, from_column_value, value, format_str = None):
    if from_column_value == from_value:
      if format_str:
        return self.get_format_str(format_str, value)
      else:
        return value
    else:
      return None

  def add_new_column_from_value(self, df, from_column_name, from_value, new_column_name, column_name_value, format_str = None):
    """
    Creates a new column (new_colum_name) when an existing column (from_column_name) contains a particular value (from_value), 
    the value for the new column is taken from another column (column_name_value). If format_str is setted, the return value is formatted.

    :param df: dataframe
    :param from_column_name: existing column to check
    :param from_value: filter value for existing column to check
    :param new_column_name: new column name
    :param column_name_value: column where to take the value for the new column
    :param format_str: format_string
    :return dataframe updated
    """
    df[new_column_name] = df.apply(lambda row: self.get_from_value(from_value, row[from_column_name], row[column_name_value], format_str), axis=1)
    return df

  def split_str_column_by_size(self, df, column_name, max_size):
    """
    Split an existing column (column_name) by size (max_size) in many new columns (with the name of exsiting column adding a suffix).

    :param df: dataframe
    :param column_name: existing column
    :param max_size: size to split
    :return dataframe updated
    """
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

  def get_label_for_precisiondate(self, value):
    return {
      'a quo': '',
      'ad quem': '',
      'ca.': 'Circa',
      'ca. ad quem': '',
      '?': 'Questionable date',
      '[?]': 'Questionable date'
    }.get(value, '')

  def add_precisiondate_column(self, df, column_name):
    """
    Creates a new column with labels for an existing column which defines precision date.

    :param df: dataframe
    :param column_name: existing column
    :return dataframe updated
    """
    df[column_name + '_LABEL'] = df.apply(lambda row: self.get_label_for_precisiondate(row[column_name]), axis=1)
    return df

  def preprocess(self, file, processed_dir):
    shutil.copyfile(file, os.path.join(processed_dir, os.path.basename(file)))
