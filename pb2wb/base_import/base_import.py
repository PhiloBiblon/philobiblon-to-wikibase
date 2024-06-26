import os

from base_import.mapper.moniker import (AnalyticMonikerMapper, BibliographyMonikerMapper, BiographyMonikerMapper,
                                        CopiesMonikerMapper, GeographyMonikerMapper, InstitutionMonikerMapper,
                                        LibraryMonikerMapper, MsEdMonikerMapper, SubjectMonikerMapper,
                                        UniformTitleMonikerMapper)
from common.settings import CLEAN_DIR
from common.wb_manager import WBManager


def get_full_input_path(bib, table):
    file = f'{bib}/csvs/{bib.lower()}_{table.value.lower()}.csv'
    return os.path.join(CLEAN_DIR, file)


def base_import(bib='BETA', table=None, skip_existing=False, dry_run=False, sample_size=0):
    print('Preparing wikibase connection ...')
    if dry_run:
        wb_manager = None
    else:
        wb_manager = WBManager()

    for mapper_class in [AnalyticMonikerMapper, BibliographyMonikerMapper, BiographyMonikerMapper, CopiesMonikerMapper,
              GeographyMonikerMapper, InstitutionMonikerMapper, LibraryMonikerMapper, MsEdMonikerMapper,
              SubjectMonikerMapper, UniformTitleMonikerMapper]:
        if table is None or table is mapper_class.TABLE:
            path = get_full_input_path(bib, mapper_class.TABLE)
            print(f'Migrating {mapper_class.TABLE} from input {path} ...')
            mapper = (mapper_class(wb_manager).
                      with_sample_size(sample_size).
                      with_dry_run(dry_run).
                      with_skip_existing(skip_existing))
            mapper.migrate( path)

    print('done.')
