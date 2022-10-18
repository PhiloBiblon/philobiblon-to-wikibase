import os
import re

# Detect empty "Dataset status" statements
PATTERN_EMPTY_DATASET_STATUS = '^(.*)\tP799\tQ(\d*)$'

class GenericPostprocessor:

  def filter(self, file, processed_file):
    with open(file, 'r') as input:
      with open(processed_file, 'w') as output:        
          for line in input:
              if not re.match(PATTERN_EMPTY_DATASET_STATUS, line):
                output.write(line)

  def postprocess(self, file, processed_dir):
    self.filter(file, os.path.join(processed_dir, os.path.basename(file)))
