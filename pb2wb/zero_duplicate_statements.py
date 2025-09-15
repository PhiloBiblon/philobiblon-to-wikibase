import pandas as pd
import requests
import json
import time
import argparse
import os
from common.settings import BASE_IMPORT_OBJECTS
import logging
from datetime import datetime

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
logging.basicConfig(
    filename=f"zero_duplicate_statements_{timestamp}.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logging.info("Logging started at %s", timestamp)

# ----- CONFIGURATION -----
FACTGRID_API_URL = 'https://database.factgrid.de/w/api.php'
KEEP_QID_FOR_P700 = 'Q447226'
KEEP_QID_FOR_P131 = 'Q256809'

'''
Example query to create CSV with duplicate P2 statements:

SELECT ?item ?pbid ?itemLabel ?p2_value ?p2_valueLabel (COUNT(?statement) AS ?count) WHERE {
  ?item wdt:P476 ?pbid.
  #FILTER(STRSTARTS(STR(?pbid), "BETA "))
  FILTER(STRSTARTS(STR(?pbid), "BITAGAP cnum "))
  ?item p:P2 ?statement.
  ?statement ps:P2 ?p2_value.
  # Get labels for easier identification of results.
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en,de,fr,es,ru,zh". }
}
GROUP BY ?pbid ?item ?itemLabel ?p2_value ?p2_valueLabel
HAVING(COUNT(?statement) > 1)
ORDER BY ?pbid ?p2_value
'''

def login():
    session = requests.Session()
    # Step 1: Get login token
    r1 = session.get(FACTGRID_API_URL, params={
        "action": "query",
        "meta": "tokens",
        "type": "login",
        "format": "json"
    })
    login_token = r1.json()['query']['tokens']['logintoken']

    # Step 2: Login
    r2 = session.post(FACTGRID_API_URL, data={
        "action": "login",
        "lgname": USERNAME,
        "lgpassword": PASSWORD,
        "lgtoken": login_token,
        "format": "json"
    })
    assert r2.json()['login']['result'] == 'Success', "Login failed"

    # Step 3: Get CSRF token
    r3 = session.get(FACTGRID_API_URL, params={
        "action": "query",
        "meta": "tokens",
        "format": "json"
    })
    csrf_token = r3.json()['query']['tokens']['csrftoken']

    return session, csrf_token

def extract_qid(url):
    return url.strip().split('/')[-1] if url else None

def should_keep(statement):
    prop = statement.get('mainsnak', {}).get('property')
    if prop == 'P476':
        return True
    if prop == 'P131':
        val = statement.get('mainsnak', {}).get('datavalue', {}).get('value', {})
        if isinstance(val, dict) and val.get('id') == KEEP_QID_FOR_P131:
            return True
    return False

def normalize_statement(statement):
    # Extract the key parts to compare entire statement
    mainsnak = statement.get("mainsnak", {})
    qualifiers = statement.get("qualifiers", {})
    # Normalize JSON representation to make it hashable/comparable
    normalized = {
        "property": mainsnak.get("property"),
        "datavalue": mainsnak.get("datavalue"),
        "datatype": mainsnak.get("datatype"),
        "snaktype": mainsnak.get("snaktype"),
        "qualifiers": qualifiers,
        "rank": statement.get("rank", "normal")
    }
    return json.dumps(normalized, sort_keys=True)

def remove_duplicate_claims(session, csrf_token, qid):
    r = session.get(FACTGRID_API_URL, params={
        "action": "wbgetclaims",
        "entity": qid,
        "format": "json"
    })
    data = r.json()
    claims = data.get("claims", {})
    logging.info(f"Found {sum(len(v) for v in claims.values())} total claims for {qid}")

    any_deleted = False
    to_delete = []  # list of GUIDs to delete

    for prop, statements in claims.items():
        # bucket statements by normalized content
        buckets = {}  # key -> list[statement]
        for st in statements:
            if should_keep(st):     # your existing “don’t touch” rule
                continue
            key = normalize_statement(st)  # your canonicalization
            buckets.setdefault(key, []).append(st)

        # decide what to keep in each bucket and mark the rest for deletion
        for key, bucket in buckets.items():
            if len(bucket) <= 1:
                continue  # no duplicates

            # pick a keeper (e.g., prefer Preferred > Normal > Deprecated; else first)
            def rank_weight(s):
                rank = s.get("rank", "normal").lower()
                return {"preferred": 3, "normal": 2, "deprecated": 1}.get(rank, 0)

            bucket.sort(key=rank_weight, reverse=True)
            keeper = bucket[0]
            dupes = bucket[1:]  # everything after keeper gets removed

            dup_guids = [st["id"] for st in dupes]
            if dup_guids:
                logging.info(f"{qid} {prop}: keeping {keeper['id']} (rank={keeper.get('rank')}) "
                             f"and deleting {len(dup_guids)} duplicates: {dup_guids}")
                to_delete.extend(dup_guids)

    # perform deletions (one-by-one; simple & safe)
    for guid in to_delete:
        if DRY_RUN:
            logging.info(f"[DRY RUN] Would delete {guid}")
            any_deleted = True
            continue
        r_del = session.post(FACTGRID_API_URL, data={
            "action": "wbremoveclaims",
            "claim": guid,
            "token": csrf_token,
            "format": "json"
        })
        try:
            result = r_del.json()
        except Exception:
            logging.error(f"Failed to parse deletion response for {guid}: {r_del.text[:500]}")
            continue
        if result.get("success") == 1:
            logging.info(f"Removed {guid}")
            any_deleted = True
        else:
            logging.error(f"Failed to remove {guid}: {result}")

    return any_deleted

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", help="Path to the CSV file with 'item' column", required=True)
    parser.add_argument("--dry_run", action='store_true', help="Perform a dry run without deleting anything")
    parser.add_argument("--instance", choices=["FACTGRID", "PBCOG"], default="FACTGRID", help="Instance to use, default is FACTGRID")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of items to process (for testing)")
    args = parser.parse_args()

    csv_path = args.csv
    global USERNAME, PASSWORD, DRY_RUN
    DRY_RUN = args.dry_run
    USERNAME = BASE_IMPORT_OBJECTS[args.instance]['WB_USER']
    PASSWORD = BASE_IMPORT_OBJECTS[args.instance]['WB_PASSWORD']
    if not os.path.exists(csv_path):
        logging.error(f"File not found: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    if 'item' not in df.columns:
        logging.error("The CSV must contain a column named 'item'.")
        return

    qids = df['item'].dropna().apply(extract_qid).unique()
    session, csrf_token = login()
    logging.info("Logged in successfully.")
    print(f"Processing {len(qids)} items from {csv_path} (dry_run={DRY_RUN})")
    count = 0
    for qid in qids:
        try:
            if args.limit and count >= args.limit:
                logging.info(f"Reached limit of {args.limit} items, stopping.")
                break
            logging.info(f"Processing {qid}")
            result = remove_duplicate_claims(session, csrf_token, qid)
            if result:
                count += 1
                logging.info(f"Processed {count} items so far.")
            time.sleep(1)  # throttle if needed
        except Exception as e:
            logging.error(f"Error processing {qid}: {e}")
    print("Done.")

if __name__ == "__main__":
    main()
