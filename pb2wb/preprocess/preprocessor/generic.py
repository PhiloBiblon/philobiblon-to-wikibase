import os
import shutil

class GenericPreprocessor:

  def preprocess(self, file, processed_dir):
    shutil.copyfile(file, os.path.join(processed_dir, os.path.basename(file)))
