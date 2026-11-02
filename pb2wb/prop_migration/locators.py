"""
Locator rules for P129 references: which property each loc_type is written to,
and repair of locators the vetting sheet has garbled.
Shared by apply_basis_migration.py (writes), run_basis_batch.py (planning) and
correct_references.py.
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


# Google Sheets reads a "volume:page" locator such as "1:227" as a time of day
# (1 h 227 min) and shows it as "4:47". The basis string is never reformatted,
# so a time-shaped loc that doesn't occur in the basis is re-derived from it.
_TIME_LOC_RE   = re.compile(r'^(\d+):(\d\d)(?::00)?$')
_BASIS_VP_RES  = (re.compile(r'(\d+)\s*:\s*(\d+)'),
                  re.compile(r'vol\.?\s*(\d+)\s*,?\s*pp?\.?\s*(\d+)', re.I))


def _as_time(volume, page):
    v, p = int(volume), int(page)
    return f'{v + p // 60}:{p % 60:02d}'


def repair_loc(basis, loc):
    """
    Return loc, or the basis's own "v:p" if loc is that locator mangled into a
    time by Google Sheets ("Arteaga 1:227" with loc "4:47" → "1:227";
    "…, vol. 2, p. 62" with loc "3:02" → "2:62").
    """
    loc = (loc or '').strip()
    m = _TIME_LOC_RE.match(loc)
    if not m:
        return loc
    shown = f'{int(m.group(1))}:{m.group(2)}'
    if shown in (basis or ''):
        return loc
    for rx in _BASIS_VP_RES:
        for v, p in rx.findall(basis or ''):
            if _as_time(v, p) == shown:
                return f'{v}:{p}'
    return loc
