import os

from common.enums import Bibliography
from common.settings import PRE_PROCESSED_DIR
from .preprocessor.analytic import AnalyticPreprocessor
from .preprocessor.bibliography import BibliographyPreprocessor
from .preprocessor.biography import BiographyPreprocessor
from .preprocessor.copies import CopiesPreprocessor
from .preprocessor.geography import GeographyPreprocessor
from .preprocessor.institution import InstitutionPreprocessor
from .preprocessor.library import LibraryPreprocessor
from .preprocessor.ms_ed import MsEdPreprocessor
from .preprocessor.subject import SubjectPreprocessor
from .preprocessor.uniform_title import UniformTitlePreprocessor


def preprocess(top_level_bib=Bibliography.BETA, table=None, qnumber_lookup_file=None, instance=None):

  pre_processed_dir = os.path.join(PRE_PROCESSED_DIR, top_level_bib.value)
  os.makedirs(pre_processed_dir, exist_ok=True)
  if qnumber_lookup_file == 'None':
      qnumber_lookup_file = None

  for processor in [AnalyticPreprocessor, BibliographyPreprocessor, BiographyPreprocessor, CopiesPreprocessor,
                    GeographyPreprocessor, InstitutionPreprocessor, LibraryPreprocessor, MsEdPreprocessor,
                    SubjectPreprocessor, UniformTitlePreprocessor]:
    if table is None or table is processor.TABLE:
      processor(top_level_bib, qnumber_lookup_file, instance).preprocess()
