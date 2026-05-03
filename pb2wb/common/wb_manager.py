import time

from wikibaseintegrator import WikibaseIntegrator, wbi_login
from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator import wbi_helpers
from wikibaseintegrator.datatypes import Item as WBItem
from wikibaseintegrator.models import Claim
from common.settings import BASE_IMPORT_OBJECTS, TEMP_DICT
from wikibaseintegrator.wbi_exceptions import MWApiError

_WRITE_DELAY = 0.5   # seconds between write calls


def _find_claim_by_guid(item, guid):
    """Return the Claim whose .id matches guid, or raise KeyError."""
    for claim in item.claims:
        if claim.id == guid:
            return claim
    raise KeyError(f'Statement GUID {guid!r} not found on item {item.id}')

# FactGrid properties
PROPERTY_INSTANCE_OF='P2'
PROPERTY_SUBCLASS_OF='P3'
PROPERTY_PHILOBIBLON_ID='P476'
PROPERTY_NOTES='P817'


class WBManager():

  def __init__(self):
    wb = TEMP_DICT['TEMP_WB']
    wbi_config['MEDIAWIKI_API_URL'] = BASE_IMPORT_OBJECTS[f'{wb}']['MEDIAWIKI_API_URL']
    wbi_config['SPARQL_ENDPOINT_URL'] = BASE_IMPORT_OBJECTS[f'{wb}']['SPARQL_ENDPOINT_URL']
    user = BASE_IMPORT_OBJECTS[f'{wb}']['WB_USER']
    print(f'Using user: {user}')
    password = BASE_IMPORT_OBJECTS[f'{wb}']['WB_PASSWORD']
    self.prefix = BASE_IMPORT_OBJECTS[f'{wb}']['SPARQL_PREFIX']
    login_instance = wbi_login.Login(user, password)
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
    try:
      print('sleeping between creations')
      item = self.wbi.item.new()
      item.labels.set(language=lang, value=label)
      item.write()
      return item
    except Exception as error:
      # Errors are usually due to rate limiting. Retry the operation after waiting for a minute
      print(f"Exception occurred. Error message: {error}")
      time.sleep(60)  # Wait for 60 seconds before retrying
      item.write()  # Retry the write operation
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
    }}""", self.prefix)
    if results['results']['bindings']:
      return self.wbi.item.get(results['results']['bindings'][0]['item']['value'].split('/')[-1])
    else:
      return None

  # search a property (P) by philobiblon id
  def get_p_by_pbid(self, pbid):
    results = wbi_helpers.execute_sparql_query(f"""SELECT ?p WHERE {{
      ?p wdt:{PROPERTY_PHILOBIBLON_ID} '{pbid}'.
      FILTER CONTAINS(str(?p), '/P')
    }}""", prefix=self.prefix)
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
      }}""", self.prefix)
    if results['results']['bindings']:
      return self.wbi.item.get(results['results']['bindings'][0]['item']['value'].split('/')[-1])
    else:
      return None

  # search a wb entity by its label
  def get_q_by_label(self, label, lang):
    label_regex = label.replace('(', '\\\\(').replace(')', '\\\\)')
    results= wbi_helpers.execute_sparql_query(f"""SELECT ?item WHERE {{
        ?item rdfs:label ?itemLabel.
        FILTER(REGEX(?itemLabel, "^{label_regex}$"@{lang}, "i")).
        FILTER CONTAINS(str(?item), '/Q')
      }}""", self.prefix)
    if results['results']['bindings']:
      return self.wbi.item.get(results['results']['bindings'][0]['item']['value'].split('/')[-1])
    else:
      return None

  def get_last_p(self):
    results= wbi_helpers.execute_sparql_query(f"""SELECT ?p WHERE {{
        ?p rdf:type wikibase:Property.
      }}
      ORDER BY DESC(STRLEN(str(?p))) DESC(?p)
      LIMIT 1""", self.prefix)
    if results['results']['bindings']:
      return self.wbi.property.get(results['results']['bindings'][0]['p']['value'].split('/')[-1])
    else:
      return None

  # ------------------------------------------------------------------
  # Statement-level mutation methods (P721 → P129 migration)
  # ------------------------------------------------------------------

  def get_statements_with_qualifier(self, item_id, qualifier_property, qualifier_value):
    """
    Return a list of (guid, claim) pairs for all statements on item_id
    that have a qualifier qualifier_property whose string value equals
    qualifier_value.

    Parameters
    ----------
    item_id           : str  e.g. 'Q1234'
    qualifier_property: str  e.g. 'P721'
    qualifier_value   : str  exact string to match

    Returns
    -------
    list of (guid: str, claim: Claim)
    """
    item = self.wbi.item.get(item_id)
    matches = []
    for claim in item.claims:
      snaks = claim.qualifiers.get(qualifier_property) or []
      for snak in snaks:
        dv = snak.datavalue
        value = dv.get('value') if isinstance(dv, dict) else None
        if value == qualifier_value:
          matches.append((claim.id, claim))
          break
    return matches

  def add_reference_to_statement(self, item_id, statement_guid, ref_property, ref_qid):
    """
    Add an item-valued reference to an existing statement.

    Fetches item_id, locates the statement by GUID, appends a reference
    with ref_property → ref_qid, and writes the item back.

    Parameters
    ----------
    item_id         : str  e.g. 'Q1234'
    statement_guid  : str  e.g. 'Q1234$abc-def-...'
    ref_property    : str  e.g. 'P129'
    ref_qid         : str  e.g. 'Q5678'

    Raises
    ------
    KeyError    if statement_guid not found on item
    MWApiError  on write failure
    """
    item  = self.wbi.item.get(item_id)
    claim = _find_claim_by_guid(item, statement_guid)

    from wikibaseintegrator.models import Reference
    ref = Reference()
    ref.add(WBItem(value=ref_qid, prop_nr=ref_property))
    claim.references.add(ref)

    time.sleep(_WRITE_DELAY)
    item.write()

  def remove_qualifier_from_statement(self, item_id, statement_guid,
                                      qualifier_property, qualifier_value):
    """
    Remove a string-valued qualifier from an existing statement.

    Fetches item_id, locates the statement by GUID, removes the first
    qualifier on qualifier_property whose string value equals
    qualifier_value, and writes the item back.

    Parameters
    ----------
    item_id            : str  e.g. 'Q1234'
    statement_guid     : str  e.g. 'Q1234$abc-def-...'
    qualifier_property : str  e.g. 'P721'
    qualifier_value    : str  exact string value to remove

    Raises
    ------
    KeyError    if statement_guid not found, or qualifier not present
    MWApiError  on write failure
    """
    item  = self.wbi.item.get(item_id)
    claim = _find_claim_by_guid(item, statement_guid)

    snaks = claim.qualifiers.get(qualifier_property) or []
    target = None
    for snak in snaks:
      dv = snak.datavalue
      value = dv.get('value') if isinstance(dv, dict) else None
      if value == qualifier_value:
        target = snak
        break

    if target is None:
      raise KeyError(
        f'Qualifier {qualifier_property}="{qualifier_value}" not found '
        f'on statement {statement_guid}'
      )

    claim.qualifiers.remove(target)

    time.sleep(_WRITE_DELAY)
    item.write()

  # run an SPARQL query
  def runSparQlQuery(self, query):
    results = wbi_helpers.execute_sparql_query(query, self.prefix)
    if results['results']['bindings']:
      return results['results']['bindings']
    else:
      return None
