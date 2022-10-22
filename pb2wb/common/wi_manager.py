import os
from pathlib import Path
from common.settings import MEDIAWIKI_API_URL, WB_USER, WB_PASSWORD

username_parts = WB_USER.split('@')

FAMILY_NAME = 'philobiblon'
MY_LANG = 'en'

USER_CONFIG_TEMPLATE = f"""
put_throttle=0
usernames['{FAMILY_NAME}']['{MY_LANG}'] = '{username_parts[0]}'
password_file = 'user-password.py'
family_files['{FAMILY_NAME}'] = '{MEDIAWIKI_API_URL}'
"""

USER_PASSWORD_TEMPLATE = f"('{username_parts[0]}', '{username_parts[1]}@{WB_PASSWORD}')"

PYWIKIBOT_DIR = './common/wi-conf'

Path(PYWIKIBOT_DIR).mkdir(parents=True, exist_ok=True)

# hack to allow pywikibot get config from a specific dir
os.environ['PYWIKIBOT_DIR'] = PYWIKIBOT_DIR

with open(f'{PYWIKIBOT_DIR}/user-config.py', 'w') as f:
  f.write(USER_CONFIG_TEMPLATE)

with open(f'{PYWIKIBOT_DIR}/user-password.py', 'w') as f:
  f.write(USER_PASSWORD_TEMPLATE)

import pywikibot

site = pywikibot.Site(MY_LANG, FAMILY_NAME)
