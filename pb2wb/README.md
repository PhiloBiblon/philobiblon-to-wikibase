# PhiloBiblon2Wikibase

Migrates base data from PhiloBiblon database to a Wikibase instance.

![PhiloBiblon import](./assets/PhiloBiblon_import.png)

Next steps assumes that you are using a Linux OS although should be similar for other OS.

## Setup environment

1. Create a new python virtual environment.
```
virtualenv .env
source .env/bin/activate
pip install -r requirements.txt
```
3. Set parameters in `common/settings.py`, for example:
```
MEDIAWIKI_API_URL=http://localhost/api.php
SPARQL_ENDPOINT_URL=http://localhost:8834/sparql
WB_USER=Admin@philobot
WB_PASSWORD=<pass>
```
__NOTE 1__: Create bot credentials to access your wikibase and fill `WB_USER` and `WB_PASSWORD` parameters. Only required `Edit existing pages` and `Create, edit, and move pages` permissions.

__NOTE 2__: If you want to create a wikibase instance from scratch, follow [this](https://github.com/faulhaber/PhiloBiblon/tree/master/philobiblon-sandbox/local).

## Run

Steps to migrate data:
1. `bash clean/mkclean.sh`: Clean raw CSVs.
2. `run_init.py`: Creates, when not exists, required P and Q Wikibase items using mapping files:
   * *Properties*: `conf/p_properties.csv`
   * *Entities*: `conf/q_items.csv`
3. `run_base_import.py`: Import base data from cleaned CSVs to Wikibase.
4. `run_preprocess.py`: Preprocess raw CSVs.
5. Import preprocessed CSVs to OpenRefine and process them.
6. `run_postprocess.py`: Postprocess QS files exported from QuickStatements.
7. Import QS files to Wikibase using QuickStatements.
8. `run_notes.py`: Import notes to talk page for each Q item.

Commands:

```
source .env/bin/activate
bash clean/mkclean.sh
python run_init.py --first-time
python run_base_import.py
python run_preprocess.py
(OpenRefine reconciliation and export)
python run_postprocess.py --force-new-statements
(QuickStatements import)
python run_notes.py
```

It is possible to process only one table too:

```
python run_preprocess.py --table <table>
(OpenRefine reconciliation and export)
python run_postprocess.py --table <table> --force-new-statements
(QuickStatements import)
python run_notes.py --table <table>
```

where `<table>` can be:
* ANALYTIC
* BIBLIOGRAPHY
* BIOGRAPHY
* COPIES
* GEOGRAPHY
* INSTITUTIONS
* LIBRARY
* MS_ED
* SUBJECT
* UNIFORM_TITLE

## Developer tips

### Run SPARQL query

1. Configure Wikibase connection properties in `common/settings.py` (`MEDIAWIKI_API_URL`, `SPARQL_ENDPOINT_URL`, `WB_USER`, `WB_PASSWORD` and `SPARQL_PREFIX`).

2. Run the query.
```
from common.wb_manager import WBManager

print('Preparing wikibase connection ...')
wb_manager = WBManager()

results = wb_manager.runSparQlQuery("SELECT ?item ?value { ?item wdt:P476 ?value }")

print(len(results))
```

### Run a simple sparql and get all results as a CSV

1. Configure Wikibase connection properties in `common/settings.py` (`MEDIAWIKI_API_URL`, `SPARQL_ENDPOINT_URL`, `WB_USER`, `WB_PASSWORD` and `SPARQL_PREFIX`).

2. Run this script. This example retrieves all items with PBIDs.
```
python util/run_simple_sparql.py --query "SELECT ?item ?value { ?item wdt:P476 ?value }"
```

### Find missing dataclips (if any)

Make a temp directory:
```
mkdir -p tmp
```
Get the pbitems (as above example):
```
python util/run_simple_sparql.py --query "SELECT ?item ?value { ?item wdt:P476 ?value }" > ./tmp/pbitems.csv
```
Extract the pbid only
```
cat ./tmp/pbitems.csv | csvcut -c value | tail +2 | sort > ./tmp/pbitems.txt
```
Remember the column names from the big dataclip
```
head -1 ../data/clean/BETA/dataclips/beta_dataclips.csv > ./tmp/dataclip-columns.txt
```
Get the full dataclips, drop the "Invalid" ones, use join to find the items tbd - put back the column names
```
cat ../data/clean/BETA/dataclips/beta_dataclips.csv  | sed 's/BETA //' | grep -v Invalid | tail +2 | sort | join -v 1 -t , - ./tmp/pbitems.txt  | (cat ./tmp/dataclip-columns.txt; cat -) > ./tmp/dataclips-tbd.csv
```
Massage into the q-items format for `run_init.py`

```
cat ./tmp/dataclips-tbd.csv | csvstack -n lang -g en - | csvstack -n QNUMBER -g '' - | csvsql --query "select QNUMBER, en as LABEL, lang as LANG, code as ALIAS, code as PBID from stdin" - > ./tmp/q_items.csv
```

### Create a lookup table of PBID to q-number

Begin as above: Get the pbitems
```
python util/run_simple_sparql.py --query "SELECT ?item ?value { ?item wdt:P476 ?value }" > ./tmp/pbitems.csv
```
Clean them up and massage them slightly
```
cat ./tmp/pbitems.csv | sed 's@http.*/Q@Q@' | csvsql --query "select value as PBID, item as QNUMBER from stdin" - > ./tmp/lookup.csv
```
