# Deploy Philobiblon Wikibase local suite

Deploy of wikibase suite for Philobiblon sandbox in your local machine that includes: *QuickStatements*, *WDQS*, *ElasticSearch* and *Openrefine-wikibase conciliator*.

## Requirements

Install this tools:

1. [Docker](https://docs.docker.com/get-docker/)
2. [Docker Compose](https://docs.docker.com/compose/install/)
3. [Python 3](https://www.python.org/downloads/)

## Preliminaries

1. It's always a good idea to pull the latest code:

```
git pull
```

2. Change into this directory:

```
cd philobiblon-sandbox/local
```

All the following commands should be done from that directory.

## Deploy a sandbox from scratch

```
docker-compose -f docker-compose.yml -f docker-compose.extra.yml -f docker-compose.reconcile.yml up -d
```

Wikibase and extra tools should be accessible (can take sometime minutes to start up all the components):

	**Wikibase**: [http://localhost](http://localhost)  
	**SPARQL frontend**: [http://localhost:8834](http://localhost:8834)  
	**QuickStatements**: [http://localhost:8840](http://localhost:8840)

## Stop a currently running local sandbox, preserving state

```
docker-compose -f docker-compose.yml -f docker-compose.extra.yml -f docker-compose.reconcile.yml stop
```

## Stop a currently running local sandbox and throw away all state

Be careful! The only difference between this command and the one above, that preserves state, is the `-v`
at the end!

```
docker-compose -f docker-compose.yml -f docker-compose.extra.yml -f docker-compose.reconcile.yml down -v
```

## Resume a stopped sandbox

This is the same command as the initial deployment:

```
docker-compose -f docker-compose.yml -f docker-compose.extra.yml -f docker-compose.reconcile.yml up -d
```

## Replace the current state with the state from the current best starter state

Note: the current state of the sandbox will be completely thrown away and replaced with the starter set.

1. Copy [this file](https://drive.google.com/file/d/1z6SYWppcGCdjq5b4smDNkHP84XaFTASF/view?usp=sharing) from the google drive

2. Unzip the contents and move or copy them to `philobiblon-sandbox/local`

3. Stop docker containers.
```
docker-compose -f docker-compose.yml -f docker-compose.extra.yml -f docker-compose.reconcile.yml stop
```

4. Do these commands

```
docker run --rm --volumes-from local_wdqs_1 -v $(pwd):/backup ubuntu bash -c "cd / && tar xvfz /backup/query-service-data.tar.gz"
docker run --rm --volumes-from local_mysql_1 -v $(pwd):/backup ubuntu bash -c "cd / && tar xvfz /backup/mediawiki-mysql-data.tar.gz"
docker run --rm --volumes-from local_elasticsearch_1 -v $(pwd):/backup ubuntu bash -c "cd / && tar xvfz /backup/elasticsearch-data.tar.gz"
docker run --rm --volumes-from local_quickstatements_1 -v $(pwd):/backup ubuntu bash -c "cd / && tar xvfz /backup/quickstatements-data.tar.gz"
```

5. Bring the sandbox up again:

```
docker-compose -f docker-compose.yml -f docker-compose.extra.yml -f docker-compose.reconcile.yml up -d
```

After this, you will find lots of items with PB IDs.

## Prepare the sandbox for running scripts

1. Prepare basic config in wikibase.
 - Create a bot
   - Login as admin to wikibase and go to http://localhost/wiki/Special:BotPasswords
      - Name: philobot
      - Select grants: `Edit existing pages` and `Create, edit, and move pages`.
    - Save password inside `pb2wb/settings.py` in `WB_PASSWORD` parameter.

2. Follow the instructions in `pd2wb` directory

## Special operations

These will probably be used rarely.

### Create backup

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

### Recover backup

1. Stop docker containers.
```
docker-compose -f docker-compose.yml -f docker-compose.extra.yml -f docker-compose.reconcile.yml stop
```

2. Restore backups

These are the same commands that are used to get the sandbox into the starter state.

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

## Other commands

* To improve performance on massive imports, you can run several job runners in parallel by using the `--scale` option:
```
docker-compose -f docker-compose.yml -f docker-compose.extra.yml -f docker-compose.reconcile.yml up -d --scale wikibase_jobrunner=8
```

## Troubleshooting

### Search in wikibase is not working

When you are using wikibase search input and no results are returned, look for this error in elasticsearch container:

```
docker logs local_elasticsearch_1 | grep "RDF store reports the last update time is before the minimum safe poll time."
```

If you get this error, then the problem is that there are data that is not processed and then ignored. You need to follow the next steps:

1. Run this query in quickstatemens to obtain the date with data:

```
SELECT * WHERE { http://wikibase.svc <http://schema.org/dateModified> ?o . }
```

2. Stop docker containers.

3. Increase parameter `WIKIBASE_MAX_DAYS_BACK` in `docker-compose.extra.yml` to include the date obtained in step 1.

4. Start docker containers.

After that search option should work again, can take some minutes process all the data.
