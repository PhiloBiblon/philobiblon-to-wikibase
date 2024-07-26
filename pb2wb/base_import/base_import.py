import os

from base_import.mapper.moniker import (AnalyticMonikerMapper, BibliographyMonikerMapper, BiographyMonikerMapper,
                                        CopiesMonikerMapper, GeographyMonikerMapper, InstitutionMonikerMapper,
                                        LibraryMonikerMapper, MsEdMonikerMapper, SubjectMonikerMapper,
                                        UniformTitleMonikerMapper)
from common.settings import CLEAN_DIR, TEMP_DICT
from common.wb_manager import WBManager


def get_full_input_path(bib, table, updated, spot):
    if updated:
        file = f'updated/{bib.lower()}/{bib.lower()}_{table.value.lower()}.csv'
        return file
    if spot:
        file = f'spot_test/{bib.lower()}/{bib.lower()}_{table.value.lower()}.csv'
        return file
    file = f'{bib}/csvs/{bib.lower()}_{table.value.lower()}.csv'
    return os.path.join(CLEAN_DIR, file)

def base_import(bib='BETA', table=None, skip_existing=False, dry_run=False, sample_size=0, updated=False, wb='PBSANDBOX', spot=False):
    print('Preparing wikibase connection ...')
    print(f'Using wikibase: {wb} and bibliography: {bib}')
    TEMP_DICT['TEMP_WB'] = wb
    TEMP_DICT['TEMP_BIB'] = bib

    if dry_run:
        wb_manager = None
    else:
        wb_manager = WBManager()

    for mapper_class in [AnalyticMonikerMapper, BibliographyMonikerMapper, BiographyMonikerMapper, CopiesMonikerMapper,
              GeographyMonikerMapper, InstitutionMonikerMapper, LibraryMonikerMapper, MsEdMonikerMapper,
              SubjectMonikerMapper, UniformTitleMonikerMapper]:
        if table is None or table is mapper_class.TABLE:
            path = get_full_input_path(bib, mapper_class.TABLE, updated, spot)
            print(f'Migrating {mapper_class.TABLE} from input {path} ...')
            mapper = (mapper_class(wb_manager).
                      with_sample_size(sample_size).
                      with_dry_run(dry_run).
                      with_skip_existing(skip_existing))
            mapper.migrate( path)

    print('done.')
