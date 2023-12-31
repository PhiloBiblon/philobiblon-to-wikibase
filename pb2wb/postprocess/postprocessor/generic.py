import os
import re
from datetime import datetime
from datetime import date

# Detect empty "Dataset status" statements
PATTERN_EMPTY_DATASET_STATUS = '^(.*)\tP799\tQ(\d*)$'

PATTERN_STATEMENT = '^Q(\d*)\tP(\d*)\t(.*)$'
PATTERN_DATE = '\+\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z/\d{1,2}'

class GenericPostprocessor:
  SPANISH_START_GREGORIAN = date(1582, 10, 15)

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
              if not re.match(PATTERN_EMPTY_DATASET_STATUS, line):
                if force_new_statements:
                  line = self.update_command(line)
                line = self.julian_dates(line)
                output.write(line)

  def postprocess(self, file, processed_dir, force_new_statements):
    self.filter(file, os.path.join(processed_dir, os.path.basename(file)), force_new_statements)
