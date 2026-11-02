"""
Tolerant readers for columns that humans edit in the vetting sheets.
"""

import re

# Charles marks approved rows with Y, but variants creep in (y, YY, yy, ...).
# Any value made only of y/Y counts as vetted.
_VETTED_RE = re.compile(r'^[yY]+$')

# The frequency column has been headed F, freq and Freqency at various times.
FREQ_NAMES = ('freq', 'f', 'frequency', 'freqency', 'frquency')


def is_vetted(value):
    return bool(_VETTED_RE.match((value or '').strip()))


def is_freq_column(name):
    return (name or '').strip().lower() in FREQ_NAMES


def freq_column(fieldnames):
    """Return the header that holds frequency, or None."""
    return next((n for n in fieldnames or [] if is_freq_column(n)), None)


def row_freq(row, default=0):
    """Frequency from a csv.DictReader row, whatever the column is called."""
    col = freq_column(row.keys())
    try:
        return int((row.get(col) or '').strip()) if col else default
    except ValueError:
        return default
