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
      - Select grants: `Edit existing pages` and `Create, edit, and move pages`.
    - Save password inside `pb2wb/settings.py` in `WB_PASSWORD` parameter.
 - Add basic properties and items to wikibase
```
cd pb2wb
virtualenv .env
source .env/bin/activate
pip install -r requirements.txt
python pb_wb_init.py
```

## Recover backup

1. Stop docker containers.
```
docker-compose -f docker-compose.yml -f docker-compose.extra.yml -f docker-compose.reconcile.yml stop
```
2. Restore backups
```
docker run --rm --volumes-from local_wdqs_1 -v $(pwd):/backup ubuntu bash -c "cd / && tar xvfz /backup/query-service-data.tar.gz"
docker run --rm --volumes-from local_mysql_1 -v $(pwd):/backup ubuntu bash -c "cd / && tar xvfz /backup/mediawiki-mysql-data.tar.gz"
docker run --rm --volumes-from local_elasticsearch_1 -v $(pwd):/backup ubuntu bash -c "cd / && tar xvfz /backup/elasticsearch-data.tar.gz"
docker run --rm --volumes-from local_quickstatements_1 -v $(pwd):/backup ubuntu bash -c "cd / && tar xvfz /backup/quickstatements-data.tar.gz"
```
3. Start docker containers.
```
docker-compose -f docker-compose.yml -f docker-compose.extra.yml -f docker-compose.reconcile.yml up -d
```

## Create backup

1. Stop docker containers.
```
docker-compose -f docker-compose.yml -f docker-compose.extra.yml -f docker-compose.reconcile.yml stop
```
2. Back up container volumes.
```
docker run --rm -it --volumes-from local_wdqs_1 -v $(pwd):/backup ubuntu tar cvfz /backup/query-service-data.tar.gz /wdqs/data
docker run --rm -it --volumes-from local_mysql_1 -v $(pwd):/backup ubuntu tar cvfz /backup/mediawiki-mysql-data.tar.gz /var/lib/mysql
docker run --rm -it --volumes-from local_elasticsearch_1 -v $(pwd):/backup ubuntu tar cvfz /backup/elasticsearch-data.tar.gz /usr/share/elasticsearch/data
docker run --rm -it --volumes-from local_quickstatements_1 -v $(pwd):/backup ubuntu tar cvfz /backup/quickstatements-data.tar.gz /quickstatements/data
```

## Other commands

* To improve performance on massive imports, you can run several job runners in parallel by using the `--scale` option:
```
docker-compose -f docker-compose.yml -f docker-compose.extra.yml -f docker-compose.reconcile.yml up -d --scale wikibase_jobrunner=8
```
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

