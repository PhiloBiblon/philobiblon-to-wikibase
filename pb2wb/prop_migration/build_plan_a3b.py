"""Build plan_a3b_20261029.tsv: A3 bases whose catalogue prefix has an ok pick in
a3_catalogue_picks.tsv or a known QID in a3_catalogue_search_terms.tsv. Local only."""
import sys, csv, re
sys.path.insert(0,'prop_migration')
import task_status as t
snap,since=t.latest_snapshot()
left=t.remaining(t.load_live(snap),t.done_since(since)); lists=t.load_group_lists()
a3={b:n for b,n in left.items() if t.classify(b,lists)=='A3'}
picks={}
for r in csv.DictReader(open('prop_migration/a3_catalogue_picks.tsv'),delimiter='\t'):
    if r['status']=='ok':
        for p in r['prefixes'].split(' | '): picks[p]=r['qid']
for r in csv.DictReader(open('prop_migration/a3_catalogue_search_terms.tsv'),delimiter='\t'):
    if r['action']=='known':
        for p in r['prefixes'].split(' | '): picks[p]=r['search_term_or_qid']
EVID=[(r'ex-?\s?libris|exlibris',      'Q418813'),
      (r'\bsellos?\b|segell',           'Q512065'),
      (r'supra-?libros',                'Q1882378'),
      (r'\bguarda',                     'Q358912'),
      (r'escudo|escut',             'Q960940')]
BARE=re.compile(r'^(?:(?:ex-?libris|sellos?|supra-?libros|ms\.?|MS|y|,|’|\s)+)$', re.I)
WHOLE={'Ex-libris y sello de la Biblioteca E. F. San Román (CCPBE)':'Ex-libris y sello de la Biblioteca E. F. San Román',
       'Ex-libris y sello de su biblioteca (CCPBE)':'Ex-libris y sello de su biblioteca',
       'Faulhaber ex-libris a colores guarda fija':'ex-libris a colores guarda fija',
       'Huntington ex-libris MS en la portada':'ex-libris MS en la portada: '}
rows=[]
for b,n in a3.items():
    s=t.strip_html(b); pre=s.split(':')[0].strip()
    if pre in picks and ':' in s:
        rest=s.split(':',1)[1].strip()
    else:
        pre=next((p for p in picks if p==s or (p in s and ':' not in p and s.startswith(p))), None)
        # non-colon forms are listed whole as prefixes
        if pre is None: continue
        rest=s[len(pre):].strip() if s.startswith(pre) else s
    rest=rest.strip(' ()[]')
    ev=[q for pat,q in EVID if re.search(pat,s,re.I)]
    desc='' if (not rest or BARE.match(rest)) else rest
    if pre in WHOLE: desc=(WHOLE[pre]+rest) if pre.startswith('Huntington ex') else WHOLE[pre]
    elif ':' not in s: desc=''
    rows.append((n,b,picks[pre],'Y','','',','.join(ev),desc,pre))
rows.sort(key=lambda r:(-r[0],r[1]))
out='prop_migration/plan_a3b_20261029.tsv'
with open(out,'w',newline='') as f:
    w=csv.writer(f,delimiter='\t')
    w.writerow(['freq','basis','qid','vetted','loc_type','loc','evidence','description'])
    for r in rows: w.writerow(r[:8])
open('prop_migration/run_a3b.txt','w').write(''.join(r[1]+'\n' for r in rows))
print(len(rows), sum(r[0] for r in rows))
for r in rows: print(r[0], '|', r[1][:70], '|', r[2], '|', r[6] or '-', '|', r[7][:50])
