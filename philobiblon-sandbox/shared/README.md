# Deploy Philobiblon Wikibase sandbox suite

Deploy of wikibase suite for Philobiblon sandbox that includes: *QuickStatements*, *WDQS*, *ElasticSearch* and *Openrefine-wikibase conciliator*.

Currently this suite is running on a Rapsberry Pi 4 using special docker images, more info [here](https://github.com/jmformenti/docker-images/tree/master/raspberrypi/wikibase). For DNS resolution is using [Duck DNS](https://www.duckdns.org/).

## Deploy from scratch

1. Up wikibase suite using docker.
```
COMPOSE_HTTP_TIMEOUT=300 docker-compose -f docker-compose.yml -f docker-compose.extra.yml -f docker-compose.reconcile.yml up -d
```
2. Create a bot
   - Login as admin to wikibase and go to http://philobiblon.duckdns.org/wiki/Special:BotPasswords
      - Name: philobot
      - Select grants: "Edit existing pages" and "Create, edit, and moves pages"
   - Save password inside `pb2wb/settings.py` in `WB_PASSWORD` parameter.
3. Update wiki.
  - Update main page:
```
<strong>Welcome to Philobiblon Wikibase sandbox.</strong>

Consult the [https://www.mediawiki.org/wiki/Special:MyLanguage/Help:Contents User's Guide] for information on using the wiki software.

==Getting started==
*[[Help:Sandbox|Getting started with the sandbox]]
*[https://www.mediawiki.org/wiki/Special:MyLanguage/Manual:Configuration_settings Configuration settings list]
*[https://www.mediawiki.org/wiki/Special:MyLanguage/Manual:FAQ MediaWiki FAQ]
*[https://lists.wikimedia.org/postorius/lists/mediawiki-announce.lists.wikimedia.org/ MediaWiki release mailing list]
*[https://www.mediawiki.org/wiki/Special:MyLanguage/Localisation#Translation_resources Localise MediaWiki for your language]
*[https://www.mediawiki.org/wiki/Special:MyLanguage/Manual:Combating_spam Learn how to combat spam on your wiki]
```
 - Create Help:Sandbox page:
```
Firsts steps to use Philobiblon Wikibase sandbox.

== Extra services ==

* Quickstatements: http://qs.philobiblon.duckdns.org:8840
* SPARQL: http://philobiblon.duckdns.org:8834
* OpenRefine reconciliation: http://philobiblon.duckdns.org:8000

== Working with OpenRefine ==

1. Probably the easy way to install OpenRefine is using its [https://www.docker.com/ docker] image:
 docker run --name openrefine -d -p 3333:3333 -v ${PATH}:/data:z felixlohmeier/openrefine:3.5.0 -i 0.0.0.0 -d /data -m 4G

where <code>${PATH}</code> is your path directory where you have the CSV files or other stuff to work with OpenRefine.


2. Take a look to its [https://openrefine.org/documentation.html docs] and specially its [https://docs.openrefine.org/ user manual].


3. To connect OpenRefine with this wikibase, use this config:

 {
   "version": "1.0",
   "mediawiki": {
     "name": "PhiloBiblon sandbox",
     "root": "http://philobiblon.duckdns.org/wiki/",
     "main_page": "http://philobiblon.duckdns.org/wiki/Main_Page",
     "api": "http://philobiblon.duckdns.org/w/api.php"
   },
   "wikibase": {
     "site_iri": "http://philobiblon.duckdns.org/entity/",
     "maxlag": 5,
     "properties": {
       "instance_of": "P1",
       "subclass_of": "P2"
     }
   },
   "reconciliation": {
     "endpoint": "http://philobiblon.duckdns.org:8000/${lang}/api"
   },
   "editgroups": {
     "url_schema": "([[:toollabs:editgroups/b/OR/${batch_id}|details]])"
   }
 }
more info [https://docs.openrefine.org/manual/wikibase/configuration#check-the-format-of-the-manifest here].


4. Happy open refining!
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

