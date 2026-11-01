"""Group the A7 strings used >= 10 times into search terms (local only).
Writes a7_top_search_terms.tsv: action (search / known / note / skip), term or QID, usages,
strings, note. Author + year (+ :page) strings are searched as "Author (Year)", the
label form of FactGrid's PhiloBiblon works; the page becomes the locator later."""
import csv, re, sys
from collections import OrderedDict

sys.path.insert(0, 'prop_migration')
import task_status as t

MIN = 10
NOTES = {'muerte', 'muerte Santillana', 'f. 1r', 'no numerats', 'fot. parc.', 'ç', 'lletra', 'sello',
         'fechas del original y del MS', 'f. 352v', 'f. 26r-', 'vuit preliminars sense numeració segu'}
KNOWN = {  # string -> (qid, note); QIDs settled earlier in this migration
    'BnF': ('Q165001', 'BnF'), 'BnF Cat.': ('Q165001', 'BnF (no catalogue item)'),
    'Wikidata (2012-)': ('Q370382', 'Wikidata'), 'Wikpedia': ('Q629842', 'Wikipedia (typo)'),
    'Faulhabe': ('Q164508', 'Faulhaber person (typo)'), 'UNC Cat.': ('Q1072181', 'A3b pick'),
    'Uppsala BU Cat.': ('Q1073646', 'A3b pick'), 'Cat. Brumario': ('Q1072148', 'A3b pick'),
    'Huntington Catalog': ('Q1072154', 'Huntington'), 'Cat. Huntington': ('Q1072154', 'Huntington'),
    'fichero RB': ('Q425097', 'Fichero (Charles 10-27)'), 'Madrid: RB fichero': ('Q425097', 'Fichero'),
    'BU Barcelona': ('Q448534', 'A3b pick'), 'Christie': ('Q899028', "Christie's (A3b)"),
}
SKIP = {'IGM, Faulhaber': 'two sources (comma compound)', 'Schiff, IGM': 'two sources (comma compound)',
        'Avenoza, García, Benítez, Ferrer del Río, Marini 2015': 'five authors'}
AUTHOR_YEAR = re.compile(r'^(?P<a>[^\d:,()]+?)\s*\(?(?P<y>1[5-9]\d\d|20[0-2]\d)(?:-\d+)?\)?\s*(?:[:,(]\s*.*)?$')
SHELFMARK = re.compile(r'^(?:BNE |BNM |UCM BH |RAE |esc\. |BnF |Colombina )(?P<s>.+)$')

snap, since = t.latest_snapshot()
left = t.remaining(t.load_live(snap), t.done_since(since))
lists = t.load_group_lists()
counts = {}
for b, n in left.items():
    if t.classify(b, lists) == 'A7':
        s = t.strip_html(b).strip()
        counts[s] = counts.get(s, 0) + n
top = sorted(((n, s) for s, n in counts.items() if n >= MIN), reverse=True)

groups = OrderedDict()
def put(action, term, s, n, note=''):
    g = groups.setdefault((action, term), {'usages': 0, 'strings': [], 'note': note})
    g['usages'] += n
    g['strings'].append(s)

for n, s in top:
    if s in NOTES:
        put('note', '', s, n, 'not a source')
    elif s in SKIP:
        put('skip', '', s, n, SKIP[s])
    elif s in KNOWN:
        put('known', KNOWN[s][0], s, n, KNOWN[s][1])
    elif (m := AUTHOR_YEAR.match(s)):
        put('search', f"{m['a'].strip()} ({m['y']})", s, n, 'author-year')
    elif (m := SHELFMARK.match(s)):
        term = 'MSS/' + m['s'] if s.startswith('BNM ') else m['s']   # BNM numbers are now BNE MSS/
        put('search', term, s, n, 'shelfmark')
    else:
        key = re.sub(r'^(Ms\.?|MS)\s+', 'Ms. ', s)                 # Ms. Zabálburu / MS Zabálburu
        key = {'Llibres del Tirant': 'Els Llibres del Tirant', 'Canc, geral': 'Canc. geral',
               'Catholic Encyclopedia ': 'Catholic Encyclopedia', 'Severin & Garcia': 'Severin & García',
               'Moñino': 'Rodríguez-Moñino', 'Martínez i Romero': 'Martínez Romero'}.get(key, key)
        put('search', key.strip(), s, n)

with open('prop_migration/a7_top_search_terms.tsv', 'w', newline='') as f:
    w = csv.writer(f, delimiter='\t')
    w.writerow(['action', 'search_term_or_qid', 'usages', 'strings', 'note'])
    for (action, term), g in sorted(groups.items(), key=lambda kv: (kv[0][0], -kv[1]['usages'])):
        w.writerow([action, term, g['usages'], ' | '.join(g['strings']), g['note']])
tot = {}
for (a, _), g in groups.items():
    tot[a] = tot.get(a, 0) + g['usages']
print(len(top), 'strings,', sum(n for n, _ in top), 'usages ->', len(groups), 'groups;', tot)
