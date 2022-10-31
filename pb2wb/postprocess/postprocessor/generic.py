import os
import re

# Detect empty "Dataset status" statements
PATTERN_EMPTY_DATASET_STATUS = '^(.*)\tP799\tQ(\d*)$'

# Statement pattern
PATTERN_STATEMENT = '^Q(\d*)\tP(\d*)\t(.*)$'

class GenericPostprocessor:

  def update_command(self, line):
    if re.match(PATTERN_STATEMENT, line):
      # Add ! prefix in property used for the statement
      return re.sub(PATTERN_STATEMENT, r'Q\1\t!P\2\t\3', line)
    else:
      return line


  def filter(self, file, processed_file, force_new_statements):
    with open(file, 'r') as input:
      with open(processed_file, 'w') as output:        
          for line in input:
              if not re.match(PATTERN_EMPTY_DATASET_STATUS, line):
                if force_new_statements:
                  line = self.update_command(line)
                output.write(line)

  def postprocess(self, file, processed_dir, force_new_statements):
    self.filter(file, os.path.join(processed_dir, os.path.basename(file)), force_new_statements)
