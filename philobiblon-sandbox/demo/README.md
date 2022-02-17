# Wikibase API demo

Script used in the Wikibase API demo.

## Requirements

Install these tools:

1. [Docker](https://docs.docker.com/get-docker/)
2. [Docker Compose](https://docs.docker.com/compose/install/)
3. [Python 3](https://www.python.org/downloads/)

## Steps

1. Clone PhiloBiblon repo.
```
git clone https://github.com/faulhaber/PhiloBiblon.git
```
2. Create Wikibase environment from scratch.
```
cd PhiloBiblon/philobiblon-sandbox/local/
docker-compose -f docker-compose.yml -f docker-compose.extra.yml up -d
```
3. Create `philobot` account: 
     Open your browser (`http://localhost`) -> Go to `Special pages` - > Go to `Bot passwords` -> Login (`admin` / `philo6wiki`) -> Create a new bot password  (Bot name: `philobot`) -> Select grants (`Edit existing pages`, `Create, Edit and move pages`) -> Create

4. Prepare python environment:
```
cd PhiloBiblon/philobiblon-sandbox/demo
virtualenv .env
source .env/bin/activate
pip install --pre wikibaseintegrator
pip install notebook
```
5. Apply patch to avoid error creating P properties with wikibaseintegrator.
```
cp p_datatype.patch .env/lib/python3.8/site-packages/wikibaseintegrator/entities
cd .env/lib/python3.8/site-packages/wikibaseintegrator/entities
patch < p_datatype.patch
```
6. Open jupyter notebook and play with the notebooks.
```
jupyter notebook
```

## Other commands

Other commands to work with our Wikibase local environment.

* Stop:
```
docker-compose -f docker-compose.yml -f docker-compose.extra.yml stop
```
* Delete services but no data:
```
docker-compose -f docker-compose.yml -f docker-compose.extra.yml -f docker-compose.reconcile.yml down
```
* Delete services and data:
```
docker-compose -f docker-compose.yml -f docker-compose.extra.yml -f docker-compose.reconcile.yml down -v
```
