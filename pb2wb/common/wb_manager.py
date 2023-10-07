from wikibaseintegrator import WikibaseIntegrator, wbi_login
from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator import wbi_helpers

from common.settings import MEDIAWIKI_API_URL, SPARQL_ENDPOINT_URL, WB_PASSWORD, WB_USER, SPARQL_PREFIX

# FactGrid properties
PROPERTY_INSTANCE_OF='P2'
PROPERTY_SUBCLASS_OF='P3'
PROPERTY_PHILOBIBLON_ID='P476'
PROPERTY_NOTES='P817'


class WBManager():

  def __init__(self):
    wbi_config['MEDIAWIKI_API_URL'] = MEDIAWIKI_API_URL
    wbi_config['SPARQL_ENDPOINT_URL'] = SPARQL_ENDPOINT_URL

    login_instance = wbi_login.Login(user=WB_USER, password=WB_PASSWORD)
    self.wbi = WikibaseIntegrator(login=login_instance)

  def get_wbi(self):
    return self.wbi

  # create new wikibase property
  def create_wb_p(self, label, lang='en', type='string'):
    p = self.wbi.property.new(datatype=type)
    p.labels.set(language=lang, value=label)
    p.write()
    return p

  # get wikibase property
  def get_wb_p(self, p_number):
    try:
      return self.wbi.property.get(p_number)
    except ValueError:
      return None

  # get or create wikibase property
  def get_or_create_wb_p(self, p_number, label):
    if p_number:
      p = self.get_wb_p(p_number)
    else:
      p = self.create_wb_p(label)
    return p

  # create wikibase item
  def create_wb_q(self, label, lang='en'):
    item = self.wbi.item.new()
    item.labels.set(language=lang, value=label)
    item.write()
    return item

  # get wikibase item
  def get_wb_q(self, q_number):
    try:
      return self.wbi.item.get(q_number)
    except ValueError:
      return None

  # search a item (Q) by philobiblon id
  def get_q_by_pbid(self, pbid):
    results = wbi_helpers.execute_sparql_query(f"""SELECT ?item WHERE {{
      ?item wdt:{PROPERTY_PHILOBIBLON_ID} '{pbid}'.
      FILTER CONTAINS(str(?item), '/Q')
    }}""", prefix = SPARQL_PREFIX)
    if results['results']['bindings']:
      return self.wbi.item.get(results['results']['bindings'][0]['item']['value'].split('/')[-1])
    else:
      return None

  # search a property (P) by philobiblon id
  def get_p_by_pbid(self, pbid):
    results = wbi_helpers.execute_sparql_query(f"""SELECT ?p WHERE {{
      ?p wdt:{PROPERTY_PHILOBIBLON_ID} '{pbid}'.
      FILTER CONTAINS(str(?p), '/P')
    }}""", prefix = SPARQL_PREFIX)
    if results['results']['bindings']:
      return self.wbi.property.get(results['results']['bindings'][0]['p']['value'].split('/')[-1])
    else:
      return None

  # search a wb entity by philobiblon dataclip value
  def get_by_dataclipvalue(self, value, q_dataclip):
    results = wbi_helpers.execute_sparql_query(f"""SELECT ?item WHERE {{
        ?item wdt:{PROPERTY_INSTANCE_OF}* wd:{q_dataclip.id}.
        ?item rdfs:label ?itemLabel.
        FILTER(CONTAINS(LCASE(?itemLabel), '{value.lower()}')).
      }}""", prefix = SPARQL_PREFIX)
    if results['results']['bindings']:
      return self.wbi.item.get(results['results']['bindings'][0]['item']['value'].split('/')[-1])
    else:
      return None

  # search a wb entity by its label
  def get_q_by_label(self, label, lang):
    results= wbi_helpers.execute_sparql_query(f"""SELECT ?item WHERE {{
        ?item rdfs:label ?itemLabel.
        FILTER(REGEX(?itemLabel, "^{label}$"@{lang}, "i")).
        FILTER CONTAINS(str(?item), '/Q')
      }}""", prefix = SPARQL_PREFIX)
    if results['results']['bindings']:
      return self.wbi.item.get(results['results']['bindings'][0]['item']['value'].split('/')[-1])
    else:
      return None

  def get_last_p(self):
    results= wbi_helpers.execute_sparql_query(f"""SELECT ?p WHERE {{
        ?p rdf:type wikibase:Property.
      }}
      ORDER BY DESC(STRLEN(str(?p))) DESC(?p)
      LIMIT 1""", prefix=SPARQL_PREFIX)
    if results['results']['bindings']:
      return self.wbi.property.get(results['results']['bindings'][0]['p']['value'].split('/')[-1])
    else:
      return None

  # run an SPARQL query
  def runSparQlQuery(self, query):
    results = wbi_helpers.execute_sparql_query(query, prefix = SPARQL_PREFIX)
    if results['results']['bindings']:
      return results['results']['bindings']
    else:
      return None
