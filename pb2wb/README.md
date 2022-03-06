# PhiloBiblon2Wikibase (beta)

Migrates base data from PhiloBiblon database to a Wikibase instance.

Next steps assumes that you are using a Linux OS.

## Setup environment

1. Clone this repo.
```
git clone https://github.com/faulhaber/PhiloBiblon.git
```
2. Create a new python virtual environment.
```
cd pb2wb
python3 -m venv .env
source .env/bin/activate
pip install -r requirements.txt
```
3. Set parameters in `settings.py`, for example:
```
MEDIAWIKI_API_URL=http://localhost/api.php
SPARQL_ENDPOINT_URL=http://localhost:8834/sparql
WB_USER=Admin@philobot
WB_PASSWORD=<pass>
```
__NOTE 1__: Create bot credentials to access your wikibase and fill `WB_USER` and `WB_PASSWORD` parameters.

__NOTE 2__: If you want to create a wikibase instance from scratch, follow [this](https://github.com/wmde/wikibase-release-pipeline/tree/main/example).

## Run

To create base data there are 3 scripts:
1. `pb_wb_init.py`: Creates, when not exists, required P and Q Wikibase items using mapping files:
   * *Properties*: `conf/p_properties.csv`
   * *Entities*: `conf/q_items.csv`
2. `import_dataclip.py`: Import dataclips from PhiloBiblon to Wikibase.
3. `import_base.py`: Import base data for each of the 10 PhiloBiblon tables (Bibliography, Biography, Geography..).

Commands:

```
cd pb2wb
source .env/bin/activate
python pb_wb_init.py
python import_dataclip.py
python import_base.py
```
