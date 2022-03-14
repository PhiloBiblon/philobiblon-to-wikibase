import re
from wb_manager import WBManager

PATTERN = 'ERROR: duplicated label,.*already has label \"([^\"]*)\".*Item\:([^\"]*)\".*PBID=([^)]*)'

print('Preparing wikibase connection ...')
wb_manager = WBManager()

with open('./log/base.log') as f:
    for line in f:
        match = re.search(PATTERN, line)
        if match:
          label = match.group(1)
          related_q_number = match.group(2)
          pbid = match.group(3)
          related_q_item = wb_manager.get_wb_q(related_q_number)
          related_pbid = related_q_item.claims.get('P4')[0].mainsnak.datavalue['value']
          print(f'{pbid}|has the same label that "{related_pbid}": "{label}"')

print('done.')