import csv
import os
import re
import textwrap
from datetime import datetime
from itertools import zip_longest

import pandas as pd

from common import enums
from common.enums import Bibliography, Table
from common.data_dictionary import DATADICT
from common.settings import (CLEAN_DIR, BASE_DATA_DIR, PRE_PROCESSED_DIR, BASE_IMPORT_OBJECTS)
from common.enums import Table

class GenericPreprocessor:

  def __init__(self, top_level_bib=Bibliography.BETA, qnumber_lookup_file=None, instance=None):
    self.top_level_bib = top_level_bib
    self.DATACLIP_RECONCILIATION_ERROR = BASE_IMPORT_OBJECTS[instance]['DATACLIP_RECONCILIATION_ERROR']
    self.BASE_OBJECT_RECONCILIATION_ERROR = BASE_IMPORT_OBJECTS[instance]['BASE_OBJECT_RECONCILIATION_ERROR']

    # MULTILANG_LENGTH_LIMIT governs labels, descriptions and aliases
    self.MULTILANG_LENGTH_LIMIT = BASE_IMPORT_OBJECTS[instance]['MULTILANG_LENGTH_LIMIT']
    # MONOLINGUALTEXT_LENGTH_LIMIT governs properties with single-language text
    self.MONOLINGUALTEXT_LENGTH_LIMIT = BASE_IMPORT_OBJECTS[instance]['MONOLINGUALTEXT_LENGTH_LIMIT']
    # STRING_LENGTH_LIMIT governs generic strings (no language context)
    self.STRING_LENGTH_LIMIT = BASE_IMPORT_OBJECTS[instance]['STRING_LENGTH_LIMIT']

    if qnumber_lookup_file:
      # if qnumber file does not begin with a slash or dot
      if not qnumber_lookup_file.startswith('/') and not qnumber_lookup_file.startswith('.'):
        # the qnumber file should be composed of the clean dir, the top_level_bib and the qnumber_lookup_file
        qnumber_lookup_file = os.path.join(BASE_DATA_DIR, qnumber_lookup_file)
      if not os.path.isfile(qnumber_lookup_file):
        raise Exception(f'qnumber_lookup_file not found: {qnumber_lookup_file}')
    self.qnumber_lookup_file = qnumber_lookup_file
    print(f'{self.qnumber_lookup_file = }')
    self.lookup_error_columns = []
    try:
      instance_enum = enums.Instance[instance]
    except ValueError:
      instance_enum = enums.Instance.OTHER

    self.instance = instance_enum.value

    self.processed_dir = os.path.join(PRE_PROCESSED_DIR, self.top_level_bib.value)
    # validate that the processed dir exists
    if not os.path.isdir(self.processed_dir):
      raise Exception(f'processed dir not found: {self.processed_dir}')

    # the dataclip_file file should be composed of the clean dir, the top_level_bib, the string 'dataclips',
    # the top_level_bib in lower case, and the string '_dataclips.csv'
    self.dataclip_file = os.path.join(CLEAN_DIR, self.top_level_bib.value, 'dataclips',
                                      self.top_level_bib.value.lower() + '_dataclips.csv')
    print(f'{self.dataclip_file = }')
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
    size_before_merge = len(df)
    matched_df = mapping[mapping[mapping_from_column].isin(df[from_column_name])]
    merged_df = pd.merge(df, mapping, left_on=from_column_name, right_on=mapping_from_column, how='left')
    size_after_merge = len(merged_df)
    if size_after_merge != size_before_merge:
      print(f'\033[31mERROR: duplicates in mapping file. {size_before_merge = } {size_after_merge = } {from_column_name = } {mapping_from_column = }\033[0m')

    def insert_default (row):
        if pd.isna(row[mapping_to_column]) and (pd.isna(row[from_column_name]) or row[from_column_name] == ''):
            return default_value
        elif pd.isna(row[mapping_to_column]) and not (pd.isna(row[from_column_name]) or row[from_column_name] == ''):
            print(f'ERROR,lookup failure,pbid,"{row[0]}",column,"{from_column_name}",value,"{row[from_column_name]}"')
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
    df = self.reconcile_by_lookup(df, fields, no_match_value=self.BASE_OBJECT_RECONCILIATION_ERROR)
    if len(self.lookup_error_columns) > 0:
      if fields[0] in self.lookup_error_columns:
        print(f'\033[31mERROR: primary key lookup errors in {fields[0]}\033[0m')
      print(f'base object lookup errors: {self.lookup_error_columns}')
    return df

  def append_bib_to_dataclip(self, df, fields):
    # append the top_level_bib to the dataclip fields for BITAGAP and BITECA only
    for field in fields:
        print(f'Appending {self.top_level_bib.value} to {field} values')
        df[field] = df[field].apply(lambda x: f"{self.top_level_bib.value} {x}" if x else x)
    return df

  def reconcile_dataclips_by_lookup(self, df, fields):
    self.lookup_error_columns = []
    print(f'using instance: {self.instance}')
    # Patch dataclip fields for FACTGRID BITECA and BITAGAP
    if self.instance == 'FACTGRID' and self.top_level_bib.value in ['BITECA', 'BITAGAP']:
        df = self.append_bib_to_dataclip(df, fields)
    df = self.reconcile_by_lookup(df, fields, no_match_value=self.DATACLIP_RECONCILIATION_ERROR)
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
    file = os.path.dirname(file) + '/' + self.instance.lower() + '_' + file.split('/')[-1]
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
    df = self.process_defaults_for_editbox(df, Table.ANALYTIC.value, 'INTERNET')
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

    # Find rows that meet the condition
    rows_to_change = df[condition]

    # Print up to 10 values from the first column of the changed rows
    num_changed = len(rows_to_change)
    sample_string = ''
    if num_changed > 0:
      first_column_name = df.columns[0]
      sample_values = rows_to_change[first_column_name].head(100).tolist()
      sample_string = f'{sample_values = }'

    print(f"Inserting {default_val = } for {key = } {num_changed = } {sample_string}")
    # Apply the default value to the key column for rows that meet the condition
    df.loc[condition, key] = default_val
    return df

  def process_defaults_for_editbox(self, df, table, editbox):
    key = DATADICT[table][editbox]['primary']
    cols = DATADICT[table][editbox]['columns']
    default_val = DATADICT[table][editbox]['default']
    df = self.insert_default_for_missing_key(df.copy(), key, cols, default_val)
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

  def truncate_long_fields(self, df, column_name, max_length):
    """
    Truncate all string values in a specified column of a pandas DataFrame that are longer than the given max_length.
    Prints a message for each truncated value with details of the row, column, and truncated value.
    Updates the df in place.

    Parameters:
    df (pd.DataFrame): The input DataFrame.
    column_name (str): The name of the column to truncate values in.
    max_length (int): The maximum allowed length for the strings.
    """
    for idx, row in df.iterrows():
      value = row[column_name]

      if isinstance(value, str) and len(value) > max_length:
        truncated_value = value[:max_length]
        first_column_value = row[df.columns[0]]  # Value from the first column of the current row

        # Print the truncation message
        print(f"Truncated {column_name} {first_column_value}")

        # Update the DataFrame with the truncated value
        df.at[idx, column_name] = truncated_value

  def truncate_dataframe(self, df):
    """
    Truncate string values in a DataFrame based on column names and specified limits.
    - Truncates all columns except the first column and those named "MONIKER" to string_limit.
    - Truncates columns named "MONIKER" to moniker_limit.

    Parameters:
    df (pd.DataFrame): The input DataFrame.
    string_limit (int): The maximum length for general string truncation.
    moniker_limit (int): The maximum length for columns named "MONIKER".

    Returns:
    pd.DataFrame: A modified copy of the original DataFrame with truncated string values.
    """
    # Step 1: Make a copy of the DataFrame
    df_copy = df.copy()

    # Step 2 & 3: Iterate through each column and apply truncation based on the column name
    for column in df_copy.columns[1:]:  # Skip the first column
      if column == "MONIKER":
        self.truncate_long_fields(df_copy, column, self.MULTILANG_LENGTH_LIMIT)
      elif column != "NOTES":
        self.truncate_long_fields(df_copy, column, self.MONOLINGUALTEXT_LENGTH_LIMIT)

    # Step 4: Return the modified DataFrame
    return df_copy

  def split_and_move(self, df, tag, value_column, split_value, split_columns):
    """
    For rows where `value_column` contains `split_value`, move values from `split_columns`
    to new columns prefixed with `tag`, and clear the original `split_columns` values.

    Parameters:
    df (pd.DataFrame): Input DataFrame
    tag (str): Prefix for new columns
    value_column (str): Column name to check for `split_value`
    split_value: Value that triggers the split
    split_columns (list of str): Columns whose values should be moved

    Returns:
    pd.DataFrame: Modified DataFrame with new columns added and original columns updated
    """
    # Create new columns with prefixed names
    mask = df[value_column] == split_value
    new_cols = [f"{tag}_{col}" for col in split_columns]
    # Create new columns, initialized with empty strings
    df[new_cols] = ""
    # Move data using the mask
    df.loc[mask, new_cols] = df.loc[mask, split_columns].values
    # Clear original columns
    df.loc[mask, split_columns] = ""

    # the df gets fragmented by the above, so we clean it up by returning a copy -- slow
    return df.copy()

  def move_single_property_columns(self, df, single_props, table):
    # each editbox should already have qnumber columns
    for editbox, single_property_columns in single_props.items():
      for clip, tag in single_property_columns.items():
        value_column = DATADICT[table.value][editbox]['primary']
        columns = [value_column] + DATADICT[table.value][editbox]['columns']
        columns_with_qnumbers = []
        for column in columns:
          columns_with_qnumbers.append(column)
          if column in DATADICT[table.value]['id_fields'] + DATADICT[table.value]['dataclip_fields']:
            columns_with_qnumbers.append(column + '_QNUMBER')
        df = self.split_and_move(df, single_property_columns[clip], value_column, clip, columns_with_qnumbers)
    return df

  def float_values_up(self, df, value_cols):
    def fill_group(group):
        for col in value_cols:
            non_empty = group.loc[group[col] != '', col]
            if not non_empty.empty:
                first_index = group.index[0]
                first_non_empty_index = non_empty.index[0]
                if first_non_empty_index != first_index: # Only clear if the first non empty value is not already in the first row
                    group.at[first_index, col] = non_empty.iloc[0]  # Assign to first row only
                    group.loc[first_non_empty_index, col] = ''  # Clear only the first occurrence
        return group
    return df.groupby(df.columns[0], group_keys=False).apply(fill_group).reset_index(drop=True)

  def propagate_values_in_groups(self, df, group_col, cols_to_propagate, test_column):
    def propagate(group):
      mask = group[test_column].notna() & (group[test_column] != '')
      if not group.empty:
        for col in cols_to_propagate:
          group.loc[mask, col] = group[col].iloc[0]
      return group

    return df.groupby(group_col, group_keys=False).apply(propagate)
