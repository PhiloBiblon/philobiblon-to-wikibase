"""Build a7_folio_notes.tsv: A7 strings that are a folio reference ("f. 1r", "ff. 2v-3r"),
alone or followed by a note ("f. 3v: “Es de ...”"), for swap_qualifier.py → P1243.
Strings naming a source ("ff. 1-23 [Dacosta]", "... BnF Cat. ...") stay in A7. Local only."""
import csv, re, sys
sys.path.insert(0, 'prop_migration')
import task_status as t

FOLIO = re.compile(r'^(?:ff?\.|fols?\.|h\.|hh\.)\s*\[?[\dIVXLCivxlc]', re.I)
SOURCE = re.compile(r'\[[A-Z][a-z]+\]|\([A-Z][a-z]+\)|Cat\.')
snap, since = t.latest_snapshot()
left = t.remaining(t.load_live(snap), t.done_since(since))
lists = t.load_group_lists()
rows, held = [], []
for b, n in left.items():
    s = t.strip_html(b).strip()
    if t.classify(b, lists) != 'A7' or not FOLIO.match(s):
        continue
    (held if SOURCE.search(s) or len(s) > 400 else rows).append((n, b, s))
for name, data in (('a7_folio_notes.tsv', rows), ('a7_folio_excluded.tsv', held)):
    with open('prop_migration/' + name, 'w', newline='') as f:
        w = csv.writer(f, delimiter='\t')
        w.writerow(['basis', 'freq', 'lang', 'text'])
        for n, b, s in sorted(data, reverse=True):
            w.writerow([b, n, 'ca', s if s != b else ''])
print('list', len(rows), sum(n for n, *_ in rows), '| excluded', len(held), sum(n for n, *_ in held))
