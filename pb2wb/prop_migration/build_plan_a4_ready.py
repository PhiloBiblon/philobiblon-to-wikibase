"""Build plan_a4_ready_20261101.tsv from vetted sheet rows that didn't convert only because
of their locator (local only):
  * "BNE MSS/2420": the QID is that manuscript, so the shelfmark locator is dropped;
  * locator type "annotation" (and typos), "ms": the note goes into a P1243 description,
    with P702 evidence for ex-libris/sello as in A3;
  * "Pathfinder" (UC Berkeley's old catalogue; the sheet has a URL as QID) → OskiCat
    Q1071201, Berkeley's catalogue item (Max 2026-11-01)."""
import csv, re, sys
from collections import Counter
sys.path.insert(0, 'prop_migration')
import task_status as t

SAME_ITEM = {'BNE MSS/2420'}
SKIP = {'IGM [?]',                                            # "?" belongs in P155, not a note
        'RBME cat.; cfr. Briquet 3528 dat. 1429/1453'}        # sheet note is from another row
QID_FOR = {'Pathfinder': 'Q1071201', 'pathfinder': 'Q1071201', 'Pathfinder: separata': 'Q1071201'}
FIXED = {'BNE MSS/11311 (IGM)': 'BNE MSS/11311'}             # sheet note says MSS/1211
NOTE_TYPES = {'annotation', 'annotaton', 'ms'}
EVID = [(r'ex-?\s?libris|exlibris', 'Q418813'), (r'\bsellos?\b|segell', 'Q512065'),
        (r'supra-?libros', 'Q1882378'), (r'\bguarda', 'Q358912'), (r'escudo|escut', 'Q960940')]
BARE = re.compile(r'^(?:(?:ex-?\s?libris|sellos?|supra-?libros|ms\.?|MS|y|,|\s)+)$', re.I)

snap, since = t.latest_snapshot()
left = t.remaining(t.load_live(snap), t.done_since(since))
lists = t.load_group_lists()
live = Counter()
for b, n in left.items():
    if t.classify(b, lists) == 'A4/A5/A10':
        live[t.strip_html(b).strip()] += n
rows = []
for r in csv.DictReader(open('prop_migration/P721-P129.tsv'), delimiter='\t'):
    s = t.strip_html(r['basis']).strip()
    if s not in live or not (r.get('vetted') or '').strip().upper().startswith('Y'):
        continue
    q, lt, loc = (r['qid'] or '').strip(), (r['loc_type'] or '').strip().lower(), (r['loc'] or '').strip()
    q = QID_FOR.get(s, q)
    if not re.fullmatch(r'Q\d+', q) or s in SKIP:
        continue
    if ': ' in s:                    # the basis's own wording beats the sheet copy
        loc = s.split(': ', 1)[1]
    loc = FIXED.get(s, loc)
    if s in SAME_ITEM or (s in QID_FOR and not loc):
        rows.append((live.pop(s), s, q, '', ''))
    elif lt in NOTE_TYPES and loc:
        ev = ','.join(qe for pat, qe in EVID if re.search(pat, loc, re.I))
        desc = '' if BARE.match(loc) else loc.strip('"“” ')
        rows.append((live.pop(s), s, q, ev, desc))
rows.sort(key=lambda r: (-r[0], r[1]))
with open('prop_migration/plan_a4_ready_20261101.tsv', 'w', newline='') as f:
    w = csv.writer(f, delimiter='\t')
    w.writerow(['freq', 'basis', 'qid', 'vetted', 'loc_type', 'loc', 'evidence', 'description'])
    for n, s, q, ev, d in rows:
        w.writerow([n, s, q, 'Y', '', '', ev, d])
open('prop_migration/run_a4_ready.txt', 'w').write(''.join(r[1] + '\n' for r in rows))
print(len(rows), 'bases,', sum(r[0] for r in rows), 'usages')
