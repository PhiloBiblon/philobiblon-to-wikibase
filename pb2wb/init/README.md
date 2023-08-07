# Utils to initialize local wikibase

## Properties

Use `read_p_factgrid.py` script to get a simple copy of FactGrid's properties and put csv result file to `conf/p_properties`.

```
python read_p_factgrid.py
```

## Q items

Get basic data from Q items in FactGrid via SPARQL queries (https://database.factgrid.de/query/) and add the result (csv format) to `conf/q_items.csv`.

### Institutions

#### Class

```
SELECT ?itemEmpty ?itemLabel  (lang(?itemLabel) as ?lang) ?pbId
WHERE
{
  ?item wdt:P476 ?pbId.
  FILTER(REGEX(?pbId, "^INSTITUTIONS\\*CLASS")).
  ?item rdfs:label ?itemLabel.
  FILTER (lang(?itemLabel) = "en")
}
```

#### Type

```
SELECT ?itemEmpty ?itemLabel  (lang(?itemLabel) as ?lang) ?pbId
WHERE
{
  ?item wdt:P476 ?pbId.
  FILTER(REGEX(?pbId, "^INSTITUTIONS\\*CLASS")).
  ?item rdfs:label ?itemLabel.
  FILTER (lang(?itemLabel) = "en")
}
```

#### Milestone class

```
SELECT ?itemEmpty ?itemLabel  (lang(?itemLabel) as ?lang) ?pbId
WHERE
{
  ?item wdt:P476 ?pbId.
  FILTER(REGEX(?pbId, "^INSTITUTIONS\\*MILESTONE_CLASS")).
  ?item rdfs:label ?itemLabel.
  FILTER (lang(?itemLabel) = "en")
}
```

#### Related institutions class

```
SELECT ?itemEmpty ?itemLabel  (lang(?itemLabel) as ?lang) ?pbId
WHERE
{
  ?item wdt:P476 ?pbId.
  FILTER(REGEX(?pbId, "^INSTITUTIONS\\*RELATED_INSCLASS")).
  ?item rdfs:label ?itemLabel.
  FILTER (lang(?itemLabel) = "en")
}
```


