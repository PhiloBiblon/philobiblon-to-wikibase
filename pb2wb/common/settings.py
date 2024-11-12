# local repo configuration - probably no need to change these

CLEAN_DIR = '../data/clean'
PRE_PROCESSED_DIR = '../data/processed/pre'
OPENREFINE_PROCESSED_DIR = '../data/processed/or'
POST_PROCESSED_DIR = '../data/processed/post'
OR_SERVER = 'https://philobiblon.cog.berkeley.edu/openrefine'

BASE_IMPORT_OBJECTS = {
    'LOCAL_WB':
      {'BIB':{
        'BETA': {'Language': 'es', 'label': 'BETA', 'qnum': 'Q4'},
        'BITECA': {'Language': 'ca', 'label': 'BITECA', 'qnum': 'Q4'},
        'BITAGAP': {'Language': 'pt', 'label': 'BITAGAP', 'qnum': 'Q4'}
        },
      'MEDIAWIKI_API_URL': "http://localhost/api.php",
      'SPARQL_ENDPOINT_URL': "http://localhost:8834/proxy/wdqs/bigdata/namespace/wdq/sparql",
      'WB_USER': 'changeme',
      'WB_PASSWORD': 'changeme',
      'SPARQL_PREFIX': None,
      'BASE_OBJECT_RECONCILIATION_ERROR': 'changeme',
      'DATACLIP_RECONCILIATION_ERROR': 'changeme',
      'P799_OK_VALUES': {} #changeme
    },
    'PBSANDBOX':
      {'BIB':{
        'BETA': {'Language': 'es', 'label': 'BETA', 'qnum': 'Q4'},
        'BITECA': {'Language': 'ca', 'label': 'BITECA', 'qnum': 'Q4'},
        'BITAGAP': {'Language': 'pt', 'label': 'BITAGAP', 'qnum': 'Q4'}
        },
      'MEDIAWIKI_API_URL': "https://pbsandbox.wikibase.cloud/w/api.php",
      'SPARQL_ENDPOINT_URL': "https://pbsandbox.wikibase.cloud/query/sparql",
      'WB_USER': 'changeme',
      'WB_PASSWORD': 'changeme',
      'SPARQL_PREFIX': """
        PREFIX wd:<https://pbsandbox.wikibase.cloud/entity/>
        PREFIX wdt:<https://pbsandbox.wikibase.cloud/prop/direct/>""",
      'BASE_OBJECT_RECONCILIATION_ERROR': 'changeme',
      'DATACLIP_RECONCILIATION_ERROR': 'changeme',
      'P799_OK_VALUES': {} #changeme
    },
    'PBCOG':
      {'BIB':{
        'BETA': {'Language': 'es', 'label': 'BETA', 'qnum': 'Q4', 'p17': 'Q5', 'p700': 'Q6'},
        'BITECA': {'Language': 'ca', 'label': 'BITECA', 'qnum': 'Q51436', 'p17': 'Q5', 'p700': 'Q6'},
        'BITAGAP': {'Language': 'pt', 'label': 'BITAGAP', 'qnum': 'Q51437', 'p17': 'Q5', 'p700': 'Q6'}
        },
      'SSH_USER': 'pi',
      'SERVER': 'philobiblon.cog.berkeley.edu',
      'MEDIAWIKI_API_URL': "https://philobiblon.cog.berkeley.edu/w/api.php",
      'SPARQL_ENDPOINT_URL': "https://philobiblon.cog.berkeley.edu/query/bigdata/namespace/wdq/sparql",
      'WB_USER': 'changeme',
      'WB_PASSWORD': 'changeme',
      'SPARQL_PREFIX': """
        PREFIX wd:<https://philobiblon.cog.berkeley.edu/entity/>
        PREFIX wdt:<https://philobiblon.cog.berkeley.edu/prop/direct/>""",
      'BASE_OBJECT_RECONCILIATION_ERROR': 'Q51453',
      'DATACLIP_RECONCILIATION_ERROR': 'Q51419',
      'P799_OK_VALUES': {
        'PHILOBILON_RECORD_CREATED': 'Q14',
        'ANALYTIC*STATUS*1C': 'Q49472',
        'ANALYTIC*STATUS*1DC': 'Q49473',
        'ANALYTIC*STATUS*1F': 'Q49474',
        'ANALYTIC*STATUS*1I': 'Q49475',
        'ANALYTIC*STATUS*1TC': 'Q49476',
        'ANALYTIC*STATUS*1TF': 'Q49477',
        'ANALYTIC*STATUS*2C': 'Q49478',
        'ANALYTIC*STATUS*2I': 'Q49479',
        'BIBLIOGRAPHY*STATUS*1C': 'Q49617',
        'BIBLIOGRAPHY*STATUS*1FC': 'Q49618',
        'BIBLIOGRAPHY*STATUS*1FI': 'Q49619',
        'BIBLIOGRAPHY*STATUS*1I': 'Q49620',
        'BIBLIOGRAPHY*STATUS*2C': 'Q49621',
        'BIBLIOGRAPHY*STATUS*2I': 'Q49622',
        'MS_ED*STATUS*1C': 'Q50708',
        'MS_ED*STATUS*1F': 'Q50709',
        'MS_ED*STATUS*1I': 'Q50710',
        'MS_ED*STATUS*2C': 'Q50711',
        'MS_ED*STATUS*2I': 'Q50712'
      }
    },
    'FACTGRID':
      {'BIB':{
        'BETA': {'Language': 'es', 'label': 'BETA', 'qnum': 'Q254471', 'p17': 'Q425065', 'p700': 'Q447226'},
        'BITECA': {'Language': 'ca', 'label': 'BITECA', 'qnum': 'Q256810', 'p17': '', 'p700': ''},
        'BITAGAP': {'Language': 'pt', 'label': 'BITAGAP', 'qnum': 'Q256809', 'p17': '', 'p700': ''}
      },
      'SSH_USER': 'pi',
      'SERVER': 'philobiblon.cog.berkeley.edu',
      'MEDIAWIKI_API_URL': "https://database.factgrid.de/w/api.php",
      'SPARQL_ENDPOINT_URL': "https://database.factgrid.de/sparql",
      'WB_USER': 'changeme',
      'WB_PASSWORD': 'changeme',
      'SPARQL_PREFIX': """
        PREFIX wd:<https://database.factgrid.de/entity/>
        PREFIX wdt:<https://database.factgrid.de/prop/direct/>""",
      'BASE_OBJECT_RECONCILIATION_ERROR': 'Q425065',
      'DATACLIP_RECONCILIATION_ERROR': 'Q518693',
      'P799_OK_VALUES': {
        'PHILOBILON_RECORD_CREATED': 'Q447227'
      }
    }
}

TEMP_DICT = {'TEMP_WB': 'PBSANDBOX', 'TEMP_BIB': 'BETA', 'DRYRUN': False}
