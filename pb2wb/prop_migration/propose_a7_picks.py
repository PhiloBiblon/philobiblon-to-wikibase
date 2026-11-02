"""Propose a QID per A7 search term from a7_top_candidates.tsv (local only).
status: auto = one plausible hit; check = several plausible hits or a guess; none = no hit."""
import csv, re, unicodedata
from collections import OrderedDict

def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()

INSPECTION = re.compile(r'inspecci[oó]n personal|personal inspection|fichero', re.I)
terms = OrderedDict()
for r in csv.DictReader(open('prop_migration/a7_top_candidates.tsv'), delimiter='\t'):
    t = terms.setdefault(r['search_term'], {'usages': r['usages'], 'strings': r['prefixes'],
                                            'note': r['note'], 'hits': []})
    if r['qid']:
        t['hits'].append((r['qid'], r['label'], r['description']))

out = []
for term, t in terms.items():
    hits = t['hits']
    status, qid, label, why = 'none', '', '', ''
    if t['note'] == 'author-year':
        works = [h for h in hits if fold(h[1]).startswith(fold(term).rstrip(')'))
                 and not INSPECTION.search(h[1])]
        if len(works) == 1:
            status, (qid, label, _) = 'auto', works[0]
            why = 'only work with this author and year'
        elif works:
            status, (qid, label, _) = 'check', works[0]
            why = f'{len(works)} works with this author and year'
        elif hits:
            status, why = 'none', 'only "inspección personal" items / other years'
    elif t['note'] == 'shelfmark':
        ms = [h for h in hits if h[1].startswith('MS') and term in h[1]]
        if len(ms) == 1:
            status, (qid, label, _) = 'auto', ms[0]
            why = 'one MS with this shelfmark'
        elif ms:
            status, (qid, label, _) = 'check', ms[0]
            why = f'{len(ms)} MS items with this shelfmark'
    elif hits:
        exact = [h for h in hits if fold(h[1]).split(',')[0].strip() == fold(term)]
        status, (qid, label, _) = ('check', exact[0] if exact else hits[0])
        why = 'label starts with the term' if exact else 'first hit — a guess'
    out.append([status, term, t['usages'], qid, label, why, t['strings'],
                ' || '.join(f'{q} {l[:60]}' for q, l, _ in hits[:5])])

with open('prop_migration/a7_top_picks.tsv', 'w', newline='') as f:
    w = csv.writer(f, delimiter='\t')
    w.writerow(['status', 'search_term', 'usages', 'qid', 'label', 'why', 'strings', 'hits'])
    w.writerows(sorted(out, key=lambda r: ('auto check none'.split().index(r[0]), -int(r[2]))))
tot = {}
for r in out:
    tot.setdefault(r[0], [0, 0])
    tot[r[0]][0] += 1
    tot[r[0]][1] += int(r[2])
print(tot)
