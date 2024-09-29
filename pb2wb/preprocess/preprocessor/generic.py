import csv
import os
import re
import textwrap
from datetime import datetime
from itertools import zip_longest

import pandas as pd

from common.enums import Bibliography
from common.data_dictionary import DATADICT
from common.settings import (CLEAN_DIR, PRE_PROCESSED_DIR, BASE_OBJECT_RECONCILIATION_ERROR,
                             DATACLIP_RECONCILIATION_ERROR)


class GenericPreprocessor:

  def __init__(self, top_level_bib=Bibliography.BETA, qnumber_lookup_file=None):
    self.top_level_bib = top_level_bib
    self.TABLE = None

    if qnumber_lookup_file:
      # if qnumber file does not begin with a slash or dot
      if not qnumber_lookup_file.startswith('/') and not qnumber_lookup_file.startswith('.'):
        # the qnumber file should be composed of the clean dir, the top_level_bib and the qnumber_lookup_file
        qnumber_lookup_file = os.path.join(CLEAN_DIR, self.top_level_bib.value, qnumber_lookup_file)
      if not os.path.isfile(qnumber_lookup_file):
        raise Exception(f'qnumber_lookup_file not found: {qnumber_lookup_file}')
    self.qnumber_lookup_file = qnumber_lookup_file
    self.lookup_error_columns = []

    self.processed_dir = os.path.join(PRE_PROCESSED_DIR, self.top_level_bib.value)
    # validate that the processed dir exists
    if not os.path.isdir(self.processed_dir):
      raise Exception(f'processed dir not found: {self.processed_dir}')

    # the dataclip_file file should be composed of the clean dir, the top_level_bib, the string 'dataclips',
    # the top_level_bib in lower case, and the string '_dataclips.csv'
    self.dataclip_file = os.path.join(CLEAN_DIR, self.top_level_bib.value, 'dataclips',
                                      self.top_level_bib.value.lower() + '_dataclips.csv')
    self.df_dataclip = pd.read_csv(self.dataclip_file, dtype=str, keep_default_na=False)

  def lookupDataclip(self, code, lang):
    cell_value = self.df_dataclip.loc[self.df_dataclip['code']==f'{self.top_level_bib.value} {code}'][lang]
    if cell_value.empty == True:
      return None
    else:
      return cell_value.values[0]

  def get_input_csv(self, table=None):
    """
    Returns the path of the input csv file by concatenating the clean dir, the top_level_bib,
    the string 'csvs', top_level_bib in lower case,  an underscore, the lower case table name, and the string '.csv'.
    """
    file = os.path.join(CLEAN_DIR, self.top_level_bib.value, 'csvs',
                        self.top_level_bib.value.lower() + '_' + table.value.lower() + '.csv')
    # validate that the file exists
    if not os.path.isfile(file):
      raise Exception(f'File not found: {file}')
    return file

  def get_dataclip_csv(self):
    """
    Returns the path of the dataclip csv file from the clean dir and  top_level_bib
    """
    file = os.path.join(CLEAN_DIR, self.top_level_bib.value, 'dataclips',
                        self.top_level_bib.value.lower() + '_dataclips.csv')
    # validate that the file exists
    if not os.path.isfile(file):
      raise Exception(f'File not found: {file}')
    return file

  def get_format_str(self, format_str, value):
    """
    Applies the format parameter to the value.

    :param format_str: format string
    :param value: value to format
    :return: formatted value
    """
    if value:
      return format_str.format(value=value)
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
    prefix_columns = class_column[:len(class_column) - 6]
    r = re.compile(f'{prefix_columns}.*')

    box_columns = list(filter(r.match, df.columns))
    condition = f'{class_column}.str.len()==0 & ((' + ' | '.join([f'{col_to_check}.str.len()>0'
                                                                  for col_to_check in box_columns]) + '))'
    check_result = df.query(condition)
    if len(check_result) > 0:
      print(f'WARNING: Class column {class_column} empty but with data in {len(check_result)} rows:')
      box_columns.insert(0, check_result.columns[0])
      json_result = check_result[box_columns].head().to_json(orient='records')
      print(json_result)
      return True
    return False

  def check_rows_empty_classes(self, df, columns_to_check=None):
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

  def get_from_value(self, from_value, from_column_value, value, format_str=None):
    if from_column_value == from_value:
      if format_str:
        return self.get_format_str(format_str, value)
      else:
        return value
    else:
      return None

  def add_new_column_from_value(self, df, from_column_name, from_value, new_column_name, column_name_value,
                                format_str=None):
    """
    Creates a new column (new_column_name) when an existing column (from_column_name) contains a particular value (from_value),
    the value for the new column is taken from another column (column_name_value). If format_str is set, the return value is formatted.

    :param df: dataframe
    :param from_column_name: existing column to check
    :param from_value: filter value for existing column to check
    :param new_column_name: new column name
    :param column_name_value: column where to take the value for the new column
    :param format_str: format_string
    :return dataframe updated
    """
    pd.options.mode.chained_assignment = 'raise'
    df_copy = df.copy()
    condition_mask = df_copy[from_column_name] == from_value
    if condition_mask.any():
      # Apply the condition to get values from column_name_value only when the condition is True
      new_column_values = df_copy[column_name_value].where(condition_mask, "")
      if format_str and new_column_values.any():
        do_format = lambda x: x if x is None or not isinstance(x, str) or x == '' else format_str.format(
          value=x)
        new_column_values = new_column_values.apply(do_format)
      df_copy[new_column_name] = new_column_values
    else:
      # Handle the case where the condition is not met
      df_copy[new_column_name] = ""

    return df_copy

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

  def add_new_column_from_mapping(self, df, from_column_name, mapping_df, mapping_from_column, mapping_to_column,
                                  new_column_name, default_value="", no_match_value="",
                                  error_if_missing=True):
    # Create a mapping DataFrame
    mapping = mapping_df[[mapping_from_column, mapping_to_column]].copy()

    # Merge the original DataFrame with the mapping DataFrame
    merged_df = pd.merge(df, mapping, left_on=from_column_name, right_on=mapping_from_column, how='left')

    def insert_default (row):
        if pd.isna(row[mapping_to_column]) and (pd.isna(row[from_column_name]) or row[from_column_name] == ''):
            return default_value
        elif pd.isna(row[mapping_to_column]) and not (pd.isna(row[from_column_name]) or row[from_column_name] == ''):
            return no_match_value
        else:
            return row[mapping_to_column]

    # Use default_value if 'from_column_name' is empty (including empty strings) and no match is found in mapping
    merged_df[new_column_name] = merged_df.apply(insert_default, axis=1)

    if error_if_missing:
      if no_match_value in merged_df[new_column_name].values:
        self.lookup_error_columns.append(from_column_name)

    # Drop unnecessary columns from the merged DataFrame
    merged_df = merged_df.drop([mapping_from_column, mapping_to_column], axis=1)

    return merged_df

  def reconcile_base_objects_by_lookup(self, df, fields):
    self.lookup_error_columns = []
    df = self.reconcile_by_lookup(df, fields, no_match_value=BASE_OBJECT_RECONCILIATION_ERROR)
    if len(self.lookup_error_columns) > 0:
      if fields[0] in self.lookup_error_columns:
        print(f'\033[31mERROR: primary key lookup errors in {fields[0]}\033[0m')
      print(f'base object lookup errors: {self.lookup_error_columns}')
    return df

  def reconcile_dataclips_by_lookup(self, df, fields):
    self.lookup_error_columns = []
    df = self.reconcile_by_lookup(df, fields, no_match_value=DATACLIP_RECONCILIATION_ERROR)
    if len(self.lookup_error_columns) > 0:
      print(f'dataclip lookup errors: {self.lookup_error_columns}')
    return df

  def reconcile_by_lookup(self, df, fields, no_match_value):
    if not self.qnumber_lookup_file:
      return df
    lookup_df = pd.read_csv(self.qnumber_lookup_file, dtype=str, keep_default_na=False)
    for field in fields:
      df = self.add_new_column_from_mapping(df, field, lookup_df, 'PBID', 'QNUMBER',
                                            field + '_QNUMBER', no_match_value=no_match_value)
      df = self.move_last_column_after(df, field)
    return df

  def write_result_csv(self, df, file):
    output_csv = os.path.join(self.processed_dir, os.path.basename(file))
    print(f'{datetime.now()} INFO: Output csv: {output_csv}')
    df.to_csv(output_csv, index=False, quoting=csv.QUOTE_ALL)

  def split_column_by_clip(self, df, clip_column: str, split_column: str, clip_base: str, clip_exts,
                           format_strs=[]):
    for clip_ext, format_str in zip_longest(clip_exts, format_strs):
      df = self.add_new_column_from_value(df, clip_column, f'{clip_base}*{clip_ext}',
                                          f'{split_column}_{clip_ext}', split_column,
                                          format_str=format_str)
      df = self.move_last_column_after(df, split_column)
    return df

  def split_internet_class(self, df):
    return self.split_column_by_clip(df, 'INTERNET_CLASS', 'INTERNET_ADDRESS',
                                     'UNIVERSAL*INTERNET_CLASS',
                                     ['EMA', 'DOI', 'CAT', 'URN', 'URI', 'URL', 'VIAF'],
                                     format_strs=['mailto:{value}'])

  def split_column_by_predicate(self, df, source_column, predicate, true_extension='true', false_extension='false'):
    """
    Splits the values of a specified column into two new columns based on a predicate function.

    Parameters:
    df (pd.DataFrame): The DataFrame to be processed.
    source_column (str): The name of the column to apply the predicate on.
    predicate (Callable[[pd.Series], bool]): A function that takes a row (pd.Series) and returns True or False.
    true_extension (Optional[str]): The suffix for the column name where predicate is True. Defaults to 'true'.
    false_extension (Optional[str]): The suffix for the column name where predicate is False. Defaults to 'false'.

    Returns:
    pd.DataFrame: The DataFrame with two new columns based on the predicate results.
    """
    true_column_name = f'{source_column}_{true_extension}'
    false_column_name = f'{source_column}_{false_extension}'

    new_df = df.copy()

    # Initialize new columns with empty strings
    new_df[true_column_name] = ''
    new_df[false_column_name] = ''

    # Apply the predicate to the source_column and populate the true and false columns
    new_df[true_column_name] = new_df.apply(lambda row: row[source_column] if predicate(row) else '', axis=1)
    new_df[false_column_name] = new_df.apply(lambda row: '' if predicate(row) else row[source_column], axis=1)

    new_df = self.move_last_column_after(new_df, source_column)
    new_df = self.move_last_column_after(new_df, source_column)

    return new_df

  def insert_default_for_missing_key(self, df, key, cols, default_val):
    """
    Inserts default_val in the 'key' column for rows where:
    - key is empty string
    - at least one value in 'cols' is not empty string

    Args:
        df: pandas DataFrame
        key: str, name of the column to insert default value
        cols: list, list of column names to check for non-empty values
        default_val: str, value to insert in the key column

    Returns:
        pandas DataFrame, the modified DataFrame
    """
    condition = (df[key] == '') | (df[key].isna())  # Check for empty string or None
    condition &= df[cols].any(axis=1)  # Check if any value in 'cols' is not empty
    # Apply the default value to the key column for rows that meet the condition
    df.loc[condition, key] = default_val
    return df

  def propagate_enlarger(self, df, key_columns, columns_to_propagate):
    def propagate_first_values(group, columns):
      for column in columns:
        first_value = group[column].iloc[0]
        group[column] = first_value
      return group

    # Apply the function to each group, but only if the group is not empty
    out_df = df.copy()
    out_df[columns_to_propagate] = out_df.groupby(key_columns, group_keys=False).apply(
      lambda group: propagate_first_values(group, columns_to_propagate))[columns_to_propagate]
    return out_df

  def add_qnumber_columns(self, df, table):
    # add new columns for the qnumbers using the lookup table if supplied
    id_fields = DATADICT[table.value]['id_fields']
    dataclip_fields = DATADICT[table.value]['dataclip_fields']
    df = self.reconcile_base_objects_by_lookup(df, id_fields)
    df = self.reconcile_dataclips_by_lookup(df, dataclip_fields)
    return df
