from enum import Enum

class Bibliography(Enum):
  BETA = 'BETA'
  BITAGAP = 'BITAGAP'
  BITECA = 'BITECA'

  def language_code(self):
    if self == Bibliography.BETA:
      return "es"
    if self == Bibliography.BITAGAP:
      return "pt"
    if self == Bibliography.BITECA:
      return "ca"


class Table(Enum):
  ANALYTIC = 'ANALYTIC'
  BIBLIOGRAPHY = 'BIBLIOGRAPHY'
  BIOGRAPHY = 'BIOGRAPHY'
  COPIES = 'COPIES'
  GEOGRAPHY = 'GEOGRAPHY'
  INSTITUTIONS = 'INSTITUTIONS'
  LIBRARY = 'LIBRARY'
  MS_ED = 'MS_ED'
  SUBJECT = 'SUBJECT'
  UNIFORM_TITLE = 'UNIFORM_TITLE'
