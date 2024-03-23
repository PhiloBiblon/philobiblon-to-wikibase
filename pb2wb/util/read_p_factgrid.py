from wikibaseintegrator import WikibaseIntegrator
from wikibaseintegrator.wbi_config import config as wbi_config
import pandas as pd

wbi_config['MEDIAWIKI_API_URL'] = 'https://database.factgrid.de/w/api.php'
wbi_config['SPARQL_ENDPOINT_URL'] = 'https://database.factgrid.de/sparql'

MAX_CONTINUOUS_NOT_FOUND = 5
LANGS = [ 'en', 'ca', 'es', 'gl', 'pt' ]

wbi = WikibaseIntegrator()

not_continuous_found = 0
n = 0
props = []
while not_continuous_found < MAX_CONTINUOUS_NOT_FOUND:
  n += 1
  p_number = f'P{n}'
  print(f'Exporting property {p_number} ..')
  try:
    p = wbi.property.get(p_number)
  except Exception as err:
    print(f'ERROR exporting {p_number}: {err}')
    props.append([p_number, None, None, None])
    not_continuous_found += 1
    continue

  for lang in LANGS:
    if p.labels.get(lang):
      props.append([p.id, p.labels.get(lang), lang, p.datatype])

  not_continuous_found = 0

properties = pd.DataFrame(props[:-MAX_CONTINUOUS_NOT_FOUND], columns=['PNUMBER', 'LABEL', 'LANG', 'TYPE'])
properties.to_csv('props.csv', index=False)

print('done.')
