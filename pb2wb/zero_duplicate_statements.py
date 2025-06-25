import pandas as pd
import requests
import json
import time
import argparse
import os

# ----- CONFIGURATION -----
FACTGRID_API_URL = 'https://database.factgrid.de/w/api.php'
USERNAME = 'Jason_Hatfield'  # Use bot password account if possible
PASSWORD = 'Password'
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

def remove_duplicate_claims(session, csrf_token, qid):
    r = session.get(FACTGRID_API_URL, params={
        "action": "wbgetclaims",
        "entity": qid,
        "format": "json"
    })
    data = r.json()
    claims = data.get("claims", {})
    print(f"Found {sum(len(v) for v in claims.values())} total claims for {qid}")

    for prop, statements in claims.items():
        seen = set()
        for statement in statements:
            guid = statement['id']
            if should_keep(statement):
                continue

            value = statement.get('mainsnak', {}).get('datavalue', {}).get('value')
            val_id = json.dumps(value, sort_keys=True) if value else "null"
            key = (prop, val_id)

            if key in seen:
                print(f"Duplicate found for {prop} = {val_id}, removing {guid}")
                if not DRY_RUN:
                    r_del = session.post(FACTGRID_API_URL, data={
                        "action": "wbremoveclaims",
                        "claim": guid,
                        "token": csrf_token,
                        "format": "json"
                    })
                    result = r_del.json()
                    if 'success' in result:
                        print(f"Removed {guid}")
                    else:
                        print(f"Failed to remove {guid}: {result}")
                else:
                    print(f"[DRY RUN] Would delete {guid}")
            else:
                seen.add(key)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", help="Path to the CSV file with 'item' column", required=True)
    parser.add_argument("--dry_run", action='store_true', help="Perform a dry run without deleting anything")
    args = parser.parse_args()

    csv_path = args.csv
    global DRY_RUN
    DRY_RUN = args.dry_run
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    if 'item' not in df.columns:
        print("The CSV must contain a column named 'item'.")
        return

    qids = df['item'].dropna().apply(extract_qid).unique()
    session, csrf_token = login()
    print("Logged in successfully.")

    for qid in qids:
        try:
            print(f"Processing {qid}")
            remove_duplicate_claims(session, csrf_token, qid)
            time.sleep(1)  # throttle if needed
        except Exception as e:
            print(f"Error processing {qid}: {e}")

if __name__ == "__main__":
    main()
