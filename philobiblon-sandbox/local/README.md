# Deploy Philobiblon Wikibase local suite

Deploy of wikibase suite for Philobiblon sandbox in your local machine that includes: *QuickStatements*, *WDQS*, *ElasticSearch* and *Openrefine-wikibase conciliator*.

## Requirements

Install this tools:

1. [Docker](https://docs.docker.com/get-docker/)
2. [Docker Compose](https://docs.docker.com/compose/install/)
3. [Python 3](https://www.python.org/downloads/)

## Deploy from scratch

1. Up wikibase suite using docker.
```
docker-compose -f docker-compose.yml -f docker-compose.extra.yml -f docker-compose.reconcile.yml up -d
```
2. Wikibase and extra tools should be accessible (can take sometime minutes to start up all the components):

	**Wikibase**: [http://localhost](http://localhost)  
	**SPARQL frontend**: [http://localhost:8834](http://localhost:8834)  
	**QuickStatements**: [http://localhost:8840](http://localhost:8840)

3. Prepare basic config in wikibase.
 - Create a bot
   - Login as admin to wikibase and go to http://localhost/wiki/Special:BotPasswords
      - Name: philobot
      - Select all grants (a refinement could be possible)
    - Save password inside `pb2wb/settings.py` in `WB_PASSWORD` parameter.
 - Add basic properties and items to wikibase
```
cd pb2wb
source .env/bin/activate
pip install -r requirements.txt
python pb_wb_init.py
```

## Other commands

* Stop:
```
docker-compose -f docker-compose.yml -f docker-compose.extra.yml -f docker-compose.reconcile.yml stop
```
* Delete services but no data:
```
docker-compose -f docker-compose.yml -f docker-compose.extra.yml -f docker-compose.reconcile.yml down
```
* Delete services and data:
```
docker-compose -f docker-compose.yml -f docker-compose.extra.yml -f docker-compose.reconcile.yml down -v
```

