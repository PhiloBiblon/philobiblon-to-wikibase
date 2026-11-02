"""Build plan_a7_ready_20261030.tsv from the 'known' rows of a7_top_search_terms.tsv and the
'auto' rows of a7_top_picks.tsv (Max OK'd 2026-10-30). Local only."""
import csv, sys
sys.path.insert(0, 'prop_migration')
import task_status as t

LOC = {'Ferrando Francés 1978: 19': ('page', '19')}
pick = {}
for r in csv.DictReader(open('prop_migration/a7_top_search_terms.tsv'), delimiter='\t'):
    if r['action'] == 'known':
        for s in r['strings'].split(' | '):
            pick[s] = r['search_term_or_qid']
for r in csv.DictReader(open('prop_migration/a7_top_picks.tsv'), delimiter='\t'):
    if r['status'] == 'auto':
        for s in r['strings'].split(' | '):
            pick[s] = r['qid']

snap, since = t.latest_snapshot()
left = t.remaining(t.load_live(snap), t.done_since(since))
rows = sorted(((n, b) for b, n in left.items() if t.strip_html(b).strip() in pick), reverse=True)
with open('prop_migration/plan_a7_ready_20261030.tsv', 'w', newline='') as f:
    w = csv.writer(f, delimiter='\t')
    w.writerow(['freq', 'basis', 'qid', 'vetted', 'loc_type', 'loc', 'evidence', 'description'])
    for n, b in rows:
        loc_type, loc = LOC.get(t.strip_html(b).strip(), ('', ''))
        w.writerow([n, b, pick[t.strip_html(b).strip()], 'Y', loc_type, loc, '', ''])
open('prop_migration/run_a7_ready.txt', 'w').write(''.join(b + '\n' for _, b in rows))
print(len(rows), 'bases,', sum(n for n, _ in rows), 'usages; strings without a live basis:',
      sorted(set(pick) - {t.strip_html(b).strip() for _, b in rows}))
