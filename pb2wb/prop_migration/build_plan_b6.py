"""Build correction_plan.b6_add.tsv: for statements converted from a compound basis
("X / Y") with only one of its sources, add a reference for each other part that has a
vetted QID. Local only; apply with correct_references.py apply."""
import csv, json, re, sys
from collections import Counter

sys.path.insert(0, 'prop_migration')
import task_status as t
from locators import LOC_PROP, repair_loc

P = 'prop_migration/'
QID = re.compile(r'Q\d+$')

cur = {}
for l in open(P + 'basis_migration_progress.jsonl'):
    try:
        r = json.loads(l)
    except ValueError:
        continue
    if r.get('guid') and r.get('qid'):
        cur[r['guid']] = r
for l in open(P + 'reference_corrections.jsonl'):
    r = json.loads(l)
    if r['status'] in ('corrected', 'already') and r['guid'] in cur and r.get('old_qid'):
        cur[r['guid']] = dict(cur[r['guid']], qid=r['new_qid'])

sheet = {}
for r in csv.DictReader(open(P + 'P721-P129.tsv'), delimiter='\t'):
    q, v = (r.get('qid') or '').strip(), (r.get('vetted') or '').strip().upper()
    if QID.match(q) and v.startswith('Y'):
        sheet.setdefault(t.strip_html(r['basis']).strip(), (q, r['label'], r['loc_type'], r['loc']))
for r in csv.DictReader(open(P + 'known_qids.tsv'), delimiter='\t'):
    if QID.match(r['qid']):
        sheet.setdefault(r['key'].strip(), (r['qid'], r['label'], '', ''))
wrong = {r['qid'] for r in csv.DictReader(open(P + 'p129_target_review.tsv'), delimiter='\t')
         if r['bucket'] == 'WRONG-KIND' and r['qid'] != 'Q196098'}
evidence = {l.split('\t')[0] for l in open(P + 'evidence_qids.tsv') if QID.match(l.split('\t')[0])}

rows, skipped = [], Counter()
for g, r in cur.items():
    if ' / ' not in r['basis']:
        continue
    for part in (t.strip_html(p).strip() for p in r['basis'].split(' / ')):
        hit = sheet.get(part)
        if not hit:
            skipped['part has no QID'] += 1
            continue
        q, label, loc_type, loc = hit
        if q == r['qid']:
            continue
        if q in wrong:
            skipped['part QID is wrong-kind (B4)'] += 1
            continue
        loc = repair_loc(part, loc)
        if loc_type not in LOC_PROP:
            loc, loc_type = '', ''
        rows.append({'kind': 'add', 'basis': r['basis'], 'item': r['item'], 'guid': g,
                     'prop': r.get('prop', ''), 'old_qid': '', 'old_label': '',
                     'new_qid': q, 'new_label': label, 'old_loc': '', 'loc_type': loc_type,
                     'loc': loc, 'old_prop': '', 'new_prop': 'P702' if q in evidence else 'P129',
                     'part': part})
rows.sort(key=lambda x: (x['basis'], x['item'], x['guid'], x['new_qid']))
with open(P + 'correction_plan.b6_add.tsv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter='\t')
    w.writeheader()
    w.writerows(rows)
print(len(rows), 'references to add on', len({x['guid'] for x in rows}), 'statements,',
      len({x['item'] for x in rows}), 'items;', dict(skipped))
