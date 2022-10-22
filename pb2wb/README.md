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
1. `clean/mkclean.sh`: Clean raw CSVs.
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
python run_postprocess.py
(QuickStatements import)
python run_notes.py
```

It is possible to process only one table too:

```
python run_preprocess.py --table <table>
(OpenRefine reconciliation and export)
python run_postprocess.py --table <table>
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
