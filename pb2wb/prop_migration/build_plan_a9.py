"""Build plan_a9_20261101.tsv: A9 compounds ("X / Y") whose every part has a vetted QID.
Each is converted with its first part's reference; build_plan_b6.py then adds the others.
Local only."""
import csv, re, sys
sys.path.insert(0, 'prop_migration')
import task_status as t
from locators import LOC_PROP, repair_loc

EXCLUDE = {'Zarco / Cuenca 2017',              # "Cuenca 2017" → Q1074415 "Cuenca", a bad match
           'Catalogus 1682 / Högberg 1919'}    # sheet gives the year 1682 as a page
QID = re.compile(r'Q\d+$')

sheet = {}
for r in csv.DictReader(open('prop_migration/P721-P129.tsv'), delimiter='\t'):
    q, v = (r.get('qid') or '').strip(), (r.get('vetted') or '').strip().upper()
    if QID.match(q) and v.startswith('Y'):
        sheet.setdefault(t.strip_html(r['basis']).strip(), (q, r['loc_type'], r['loc']))
for r in csv.DictReader(open('prop_migration/known_qids.tsv'), delimiter='\t'):
    if QID.match(r['qid']):
        sheet.setdefault(r['key'].strip(), (r['qid'], '', ''))
wrong = {r['qid'] for r in csv.DictReader(open('prop_migration/p129_target_review.tsv'), delimiter='\t')
         if r['bucket'] == 'WRONG-KIND' and r['qid'] != 'Q196098'}

snap, since = t.latest_snapshot()
left = t.remaining(t.load_live(snap), t.done_since(since))
lists = t.load_group_lists()
rows = []
for b, n in left.items():
    s = t.strip_html(b).strip()
    if t.classify(b, lists) != 'A9' or s in EXCLUDE:
        continue
    parts = [p.strip() for p in s.split(' / ')]
    hits = [sheet.get(p) for p in parts]
    if not all(hits) or any(h[0] in wrong for h in hits):
        continue
    qid, loc_type, loc = hits[0]
    loc = repair_loc(parts[0], loc)
    if loc_type not in LOC_PROP:
        loc_type, loc = '', ''
    rows.append((n, b, qid, loc_type, loc))
rows.sort(key=lambda r: (-r[0], r[1]))
with open('prop_migration/plan_a9_20261101.tsv', 'w', newline='') as f:
    w = csv.writer(f, delimiter='\t')
    w.writerow(['freq', 'basis', 'qid', 'vetted', 'loc_type', 'loc', 'evidence', 'description'])
    for n, b, q, lt, l in rows:
        w.writerow([n, b, q, 'Y', lt, l, '', ''])
open('prop_migration/run_a9.txt', 'w').write(''.join(r[1] + '\n' for r in rows))
print(len(rows), 'bases,', sum(r[0] for r in rows), 'usages')
