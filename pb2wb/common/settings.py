# local repo configuration - probably no need to change these

CLEAN_DIR = '../data/clean'
PRE_PROCESSED_DIR = '../data/processed/pre'
OPENREFINE_PROCESSED_DIR = '../data/processed/or'
POST_PROCESSED_DIR = '../data/processed/post'

# Wikibase-instance-specific Settings
# Be careful not to check in secrets!

# local wikibase
MEDIAWIKI_API_URL = 'http://localhost/api.php'
SPARQL_ENDPOINT_URL = 'http://localhost:8834/proxy/wdqs/bigdata/namespace/wdq/sparql'
WB_USER = 'changeme'
WB_PASSWORD = 'changeme'
SPARQL_PREFIX = None

BASE_OBJECT_RECONCILIATION_ERROR = 'changeme'
DATACLIP_RECONCILIATION_ERROR = 'changeme'

# pbsandbox.cloud

MEDIAWIKI_API_URL = "https://pbsandbox.wikibase.cloud/w/api.php"
SPARQL_ENDPOINT_URL = 'https://pbsandbox.wikibase.cloud/query/sparql'

WB_USER = 'changeme'
WB_PASSWORD = 'changeme'
SPARQL_PREFIX = """
PREFIX wd: <https://pbsandbox.wikibase.cloud/entity/>
PREFIX wdt: <https://pbsandbox.wikibase.cloud/prop/direct/>
"""

BASE_OBJECT_RECONCILIATION_ERROR = 'changeme'
DATACLIP_RECONCILIATION_ERROR = 'changeme'

# pb.cog

MEDIAWIKI_API_URL = "https://philobiblon.cog.berkeley.edu/w/api.php"
SPARQL_ENDPOINT_URL = "https://philobiblon.cog.berkeley.edu/query/bigdata/namespace/wdq/sparql"
WB_USER = 'changeme'
WB_PASSWORD = 'changeme'
SPARQL_PREFIX = """
PREFIX wd:<https://philobiblon.cog.berkeley.edu/entity/>
PREFIX wdt:<https://philobiblon.cog.berkeley.edu/prop/direct/>
"""

BASE_OBJECT_RECONCILIATION_ERROR = 'Q51453'
DATACLIP_RECONCILIATION_ERROR = 'Q51419'

BASE_IMPORT_OBJECTS = {
    'LOCAL_WB':
      {'BIB':{
        'BETA': {'Language': 'es', 'label': 'BETA', 'qnum': 'changeme'},
        'BITECA': {'Language': 'ca', 'label': 'BITECA', 'qnum': 'changeme'},
        'BITAGAP': {'Language': 'pt', 'label': 'BITAGAP', 'qnum': 'changeme'}
        },
      'MEDIAWIKI_API_URL': "http://localhost/api.php",
      'SPARQL_ENDPOINT_URL': "http://localhost:8834/proxy/wdqs/bigdata/namespace/wdq/sparql",
      'WB_USER': 'changeme',
      'WB_PASSWORD': 'changeme',
      'SPARQL_PREFIX': None,
      'BASE_OBJECT_RECONCILIATION_ERROR': 'changeme',
      'DATACLIP_RECONCILIATION_ERROR': 'changeme'
    },
    'PBSANDBOX':
      {'BIB':{
        'BETA': {'Language': 'es', 'label': 'BETA', 'qnum': 'changeme'},
        'BITECA': {'Language': 'ca', 'label': 'BITECA', 'qnum': 'changeme'},
        'BITAGAP': {'Language': 'pt', 'label': 'BITAGAP', 'qnum': 'changeme'}
        },
      'MEDIAWIKI_API_URL': "https://pbsandbox.wikibase.cloud/api.php",
      'SPARQL_ENDPOINT_URL': "https://pbsandbox.wikibase.cloud/query/bigdata/namespace/wdq/sparql",
      'WB_USER': 'changeme',
      'WB_PASSWORD': 'changeme',
      'SPARQL_PREFIX': """
        PREFIX wd:<https://pbsandbox.wikibase.cloud/entity/>
        PREFIX wdt:<https://pbsandbox.wikibase.cloud/prop/direct/>""",
      'BASE_OBJECT_RECONCILIATION_ERROR': 'changeme',
      'DATACLIP_RECONCILIATION_ERROR': 'changeme'
    },
    'PBCOG':
      {'BIB':{
        'BETA': {'Language': 'es', 'label': 'BETA', 'qnum': 'Q4'},
        'BITECA': {'Language': 'ca', 'label': 'BITECA', 'qnum': 'Q51436'},
        'BITAGAP': {'Language': 'pt', 'label': 'BITAGAP', 'qnum': 'Q51437'}
        },
      'MEDIAWIKI_API_URL': "https://philobiblon.cog.berkeley.edu/w/api.php",
      'SPARQL_ENDPOINT_URL': "https://philobiblon.cog.berkeley.edu/query/bigdata/namespace/wdq/sparql",
      'WB_USER': 'changeme',
      'WB_PASSWORD': 'changeme',
      'SPARQL_PREFIX': """
        PREFIX wd:<https://philobiblon.cog.berkeley.edu/entity/>
        PREFIX wdt:<https://philobiblon.cog.berkeley.edu/prop/direct/>""",
      'BASE_OBJECT_RECONCILIATION_ERROR': 'Q51453',
      'DATACLIP_RECONCILIATION_ERROR': 'Q51419'
    },
    'FACTGRID': {
    'BETA': {'Language': 'es', 'label': 'BETA', 'qnum': 'changeme'},
    'BITECA': {'Language': 'ca', 'label': 'BITECA', 'qnum': 'changeme'},
    'BITAGAP': {'Language': 'pt', 'label': 'BITAGAP', 'qnum': 'changeme'}
    },
      'MEDIAWIKI_API_URL': "",
      'SPARQL_ENDPOINT_URL': "",
      'WB_USER': 'changeme',
      'WB_PASSWORD': 'changeme',
      'SPARQL_PREFIX': """'changeme'
        """,
      'BASE_OBJECT_RECONCILIATION_ERROR': 'changeme',
      'DATACLIP_RECONCILIATION_ERROR': 'changeme'
    }
