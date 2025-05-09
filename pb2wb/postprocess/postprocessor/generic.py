import os
import re
from datetime import datetime
from datetime import date

from common.settings import BASE_IMPORT_OBJECTS

PATTERN_STATEMENT = r'^Q(\d*)\tP(\d*)\t(.*)$'
PATTERN_DATE = r'\+\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z/\d{1,2}'


class GenericPostprocessor:
  SPANISH_START_GREGORIAN = date(1582, 10, 15)

  def check_empty_p799(self, s):
    l = s.split('\t')
    if len(l) == 3 and l[1] == 'P799' and l[2].lstrip('\"').rstrip("\n"'\"') in self.P799_OK_VALUES.values():
      return True
    return False

  def check_redundant_p146(self, line):
    l = line.split('\t')
    if len(l) >= 3 and l[1] == 'P146' and (
      l[0] == l[2].strip('"').split("/wiki/Item:")[-1]
      or "https://database.factgrid.de/wiki/Item:" in l[2]
      or "https://www.wikidata.org/wiki/" in l[2]
    ):
      print(f"Removing P146 statement: {line}")
      return True
    return False

  def remove_p12(self, line):
    omitted_q_items = {"Q1075316", "Q152233", "Q1075318", "Q370382", "Q1292931"}
    fields = line.split('\t')
    if len(fields) >= 3 and fields[1] == 'P12':
        obj_value = fields[2].strip('"').strip()
        if obj_value in omitted_q_items:
            print(f"Removing P12 statement: {line}")
            return True
    return False

  def check_errors(self, line):
    for error in self.ERROR_OBJECTS:
      if error in line:
        with open(self.error_file, 'a') as f:
          print(f"Error object found: {line}")
          f.write(line)
        return True
    return False

  def update_command(self, line):
    if re.match(PATTERN_STATEMENT, line):
      # Add ! prefix in property used for the statement
      return re.sub(PATTERN_STATEMENT, r'Q\1\t!P\2\t\3', line)
    else:
      return line

  def julian_dates(self, line):
    for match in re.findall(PATTERN_DATE, line):
      # get wikibase date precision: https://www.wikidata.org/wiki/Help:Dates
      precision = int(match[match.index('/')+1:])
      if precision == 11:
        date = datetime.strptime(match[1:11], '%Y-%m-%d').date()
      elif precision == 10:
        date = datetime.strptime(match[1:8], '%Y-%m').date()
      elif precision == 9:
        date = datetime.strptime(match[1:5], '%Y').date()
      if date < self.SPANISH_START_GREGORIAN:
        line = re.sub('\\' + match, match + '/J', line)
    return line

  def filter(self, file, processed_file, force_new_statements):
    with open(file, 'r') as input:
      with open(processed_file, 'w') as output:        
          for line in input:
              if self.check_redundant_p146(line) or self.remove_p12(line) or self.check_errors(line):
                continue
              if not self.check_empty_p799(line):
                if force_new_statements:
                  line = self.update_command(line)
                line = self.julian_dates(line)
                output.write(line)

  def postprocess(self, file, processed_dir, force_new_statements, instance):
    self.P799_OK_VALUES = BASE_IMPORT_OBJECTS[instance]['P799_OK_VALUES']
    self.ERROR_OBJECTS = [BASE_IMPORT_OBJECTS[instance]['BASE_OBJECT_RECONCILIATION_ERROR'], BASE_IMPORT_OBJECTS[instance]['DATACLIP_RECONCILIATION_ERROR']]
    self.error_file = f'errors_{file}'
    self.filter(file, os.path.join(processed_dir, os.path.basename(file)), force_new_statements)
