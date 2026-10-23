"""
Locator rules for P129 references: which property each loc_type is written to.
Shared by apply_basis_migration.py (writes) and run_basis_batch.py (planning).
"""

import re

LOC_PROP = {
    'page':     'P54',
    'folio':    'P100',
    'number':   'P90',
    'footnote': 'P54',   # Charles 2026-10-20: footnotes are recorded as pages ("26n")
    'volume':   'P105',
}

# "I:286", "II: 335", "3:45-50", "V.12" → volume + page
_VOL_PAGE_SPLIT_RE = re.compile(r'^\s*([IVXLCDM]+|\d+)\s*[:.]\s*(.+?)\s*$')


def locator_snaks(loc, loc_type):
    """
    Return [(prop, value), ...] for a locator.

    Volume locators that carry a page are split into P105 (volume) + P54 (page);
    a bare volume or an unparseable string goes under P105 whole.
    """
    loc = (loc or '').strip()
    prop = LOC_PROP.get(loc_type)
    if not loc or not prop:
        return []
    if loc_type == 'volume':
        m = _VOL_PAGE_SPLIT_RE.match(loc)
        if m:
            return [(LOC_PROP['volume'], m.group(1)), (LOC_PROP['page'], m.group(2))]
    return [(prop, loc)]
