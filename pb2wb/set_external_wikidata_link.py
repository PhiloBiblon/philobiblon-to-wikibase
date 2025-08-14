import requests
import pandas as pd
from common.settings import BASE_IMPORT_OBJECTS
import time
import argparse
import logging
import datetime

timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
# Enable debug logging
# Set up logging
logging.basicConfig(
    filename=f"set_wikidata_{timestamp}.log", 
    filemode="a", 
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logging.info("Logging started at %s", timestamp)

# Example SPARQL query to fetch items with P146 statements and wikidata.org in the value
'''
SELECT DISTINCT ?item ?pbid ?online_info ?link
WHERE {
  ?item wdt:P476 ?pbid .
  ?item wdt:P146 ?online_info .
  FILTER (CONTAINS(STR(?pbid), 'BETA'))
  FILTER (CONTAINS(STR(?online_info), "wikidata.org/wiki/Q")) # Filter for "wikidata.org" in P146 value
  #OPTIONAL { ?link schema:about ?item ; schema:isPartOf <https://www.wikidata.org/> . }
  #FILTER ( !bound(?link) || STR(?link) != STR(?online_info) )  # Check for mismatch
}
'''

# Configuration
wb = 'FACTGRID' # 'PBCOG' or 'FACTGRID'
user = BASE_IMPORT_OBJECTS[f'{wb}']['WB_USER']
password = BASE_IMPORT_OBJECTS[f'{wb}']['WB_PASSWORD']
PROPERTY = "P146"  # The property for online links
factgrid_api_url = "https://database.factgrid.de/w/api.php"  # Replace with your PBCOG API URL if needed
site_code = "wikidatawiki" #Site code for wikidata

# Authenticate
def login():
    session = requests.Session()
    login_token = session.get(factgrid_api_url, params={"action": "query", "meta": "tokens", "type": "login", "format": "json"}).json()['query']['tokens']['logintoken']
    session.post(factgrid_api_url, data={"action": "login", "lgname": user, "lgpassword": password, "lgtoken": login_token, "format": "json"}, timeout=30)
    csrf_token = session.get(factgrid_api_url, params={"action": "query", "meta": "tokens", "format": "json"}).json()['query']['tokens']['csrftoken']
    logging.info(f"CSRF Token: {csrf_token}")
    return session, csrf_token

def process_query_csv(session, csrf_token, CSV_FILE, delete_link=False):
    count = 0
    # Load the CSV file into a DataFrame
    df = pd.read_csv(CSV_FILE, names=['item', 'pbid', 'online_info', 'link'])

    # Extract the Q numbers from the URLs
    df['item'] = df['item'].str.extract(r'(Q\d+)', expand=False)
    df['online_info'] = df['online_info'].str.extract(r'(Q\d+)', expand=False)
    df['link'] = df['link'].str.extract(r'(Q\d+)', expand=False)

    # Condition 1: Rows where `online_info` exists but `link` does not exist
    df_no_link = df[df['online_info'].notna() & df['link'].isna()]
    logging.info("Rows where 'online_info' exists but 'link' does not:")
    logging.info(f"Total rows with 'online_info' but no 'link': {len(df_no_link)}")
    # Iterate over the rows and set the sitelinks
    for _, row in df_no_link.iterrows():
        if limit is not None and count >= limit:
            logging.info(f"Reached limit of {limit}.")
            return
        count += 1
        factgrid_qid = row['item']
        wikidata_qid = row['online_info']
        logging.info(f"FactGrid QID: {factgrid_qid}, Wikidata QID: {wikidata_qid}")
        if delete_link:
            claim_response = find_claims(session, factgrid_api_url, factgrid_qid)
            if claim_response:
                # Delete existing claims for P146 where the claim value matches a wikidata url
                logging.info(f"Found existing claim for {factgrid_qid}: {claim_response}")
                del_response = delete_claim(session, factgrid_api_url, csrf_token, claim_response)
                if del_response:
                    logging.info(f"Deleted matching P146 claims for {factgrid_qid}")
                else:
                    logging.error(f"Failed to delete existing link for {factgrid_qid}")
        else:
        # Set the sitelink for the FactGrid item
            response = set_factgrid_sitelink(session, factgrid_api_url, factgrid_qid, wikidata_qid, site_code, csrf_token)
            if response:
                logging.info(f"Set sitelink for {factgrid_qid}: {response}")
            else:
                logging.error(f"Failed to set sitelink for {factgrid_qid}")

    # Condition 2: Rows where both `online_info` and `link` exist but do not match
    df_mismatches = df[df['online_info'].notna() & df['link'].notna() & (df['online_info'] != df['link'])]
    # Remove duplicates by `item`, keeping the first occurrence
    df_mismatches = df_mismatches.drop_duplicates(subset='item')
    logging.info("Rows where both 'online_info' and 'link' exist but do not match:")
    logging.info(f"Total mismatched rows: {len(df_mismatches)}")
    #print(df_mismatches)

def process_qs_file(session, csrf_token, qs_file):
    logging.info(f"Processing QS file: {qs_file}")
    item_list = []
    count = 0
    claim_response = None
    item_check = False
    with open(qs_file, 'r') as f:
        lines = f.readlines()
    for line in lines:
        #print(line)
        line_match = False
        if limit is not None and count >= limit:
            logging.info(f"Reached limit of {limit} entries.")
            return
        line = line.split("\t")
        if len(line) < 3:
            continue
        item = line[0].split('/')[-1]
        if item in item_list:
            item_check = True
        else:
            item_check = False
        item_list.append(item)
        if not item_check:
            #print(f"Checking if item: {item} has claims.")
            claim_response = find_claims(session, factgrid_api_url, item)

        # Delete claims supplied in the guid_list
        if claim_response:
            logging.info("Found existing claims for %s: %s", item, claim_response)
            for claim_id in claim_response:
                delete_claim(session, factgrid_api_url, csrf_token, claim_id)
                item_list.remove(item)  # Remove item from list after deletion

        if line[1] == 'P146' and "wikidata.org/wiki/Q" in line[2]:
            logging.info(f"Processing line: {line}")
            online_info = line[2].strip('"').split('/')[-1]
            logging.info(f"FactGrid QID: {item}, Wikidata QID: {online_info}")
            line_match = True

        if line[1] == 'P12' and ('Q370382' in line[2] or 'Q1075316' in line[2]) and 'P90' in line:
            logging.info(f"Processing line: {line}")
            idx = line.index("P90")
            if idx + 1 < len(line):
                p90_value = line[idx + 1].strip().strip('"')
            online_info = p90_value
            logging.info(f"FactGrid QID: {item}, Wikidata QID: {online_info}")
            line_match = True

        if not line_match:
            continue
        response = set_factgrid_sitelink(session, factgrid_api_url, item, online_info, site_code, csrf_token)
        count += 1
        if response:
            logging.info("Set sitelink for %s: %s", item, response)
        else:
            logging.error("Failed to set sitelink for %s", item)
        # Sleep to avoid throttling
        time.sleep(.5)  # Avoid throttling
    print(f"Completed processing {count} entries from {qs_file}")

def find_claims(session, factgrid_api_url, factgrid_qid):
    params = {
        "action": "wbgetclaims",
        "entity": factgrid_qid,
        "format": "json"
    }
    try:
        r = session.get(factgrid_api_url, params=params, timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Request failed: {e}")
        return []

    try:
        data = r.json()
    except ValueError:
        logging.error(f"Invalid JSON for {factgrid_qid}: {r.text[:200]}")
        return []

    claims = data.get("claims", {})
    logging.info(f"Found {sum(len(v) for v in claims.values())} total claims for {factgrid_qid}")
    guid_list = []
    for prop in ('P146', 'P12'):
        for statement in claims.get(prop, []):
            val = statement.get('mainsnak', {}).get('datavalue', {}).get('value', {})
            logging.info(f"Checking claim: {statement}")
            if prop == "P146":
                if isinstance(val, str) and val in ["wikidata.org/wiki/Q", f"https://database.factgrid.de/wiki/Item:{factgrid_qid}"]:
                    logging.info(f"Found matching claim for {factgrid_qid}: {statement}")
                    guid = statement['id']
                    guid_list.append(guid)
            elif prop == "P12":
                if isinstance(val, dict) and val.get("id") in ["Q370382", "Q1075316"]:
                    logging.info(f"Found matching wikidata claim for {factgrid_qid}: {statement}")
                    qualifiers = statement.get('qualifiers', {})
                    if 'P90' in qualifiers:
                        logging.info(f"Found P90 qualifier for {factgrid_qid}: {qualifiers['P90']}")
                        P90_value = qualifiers['P90'][0]['datavalue']['value']
                        if P90_value.startswith("Q"):
                            logging.info(f"Found P90 {P90_value} for {factgrid_qid}")
                            guid = statement['id']
                            guid_list.append(guid)
                elif isinstance(val, dict) and val.get("id") in ["Q152233", "Q1075318"]:
                    logging.info(f"Found matching factgrid claim for {factgrid_qid}: {statement}")
                    qualifiers = statement.get('qualifiers', {})
                    if 'P90' in qualifiers:
                        logging.info(f"Found P90 qualifier for {factgrid_qid}: {qualifiers['P90']}")
                        P90_value = qualifiers['P90'][0]['datavalue']['value']
                        if P90_value == factgrid_qid:
                            logging.info(f"Found matching P90 {P90_value} for {factgrid_qid}")
                            # Add the claim ID to the list
                            guid = statement['id']
                            guid_list.append(guid)
    # If we found any matching claims, return their IDs
    if guid_list:
        logging.info(f"Found matching claims for {factgrid_qid}: {guid_list}")
        return guid_list
    #else:
        # No matching claims found
        #logging.info("No matching claims found for %s", factgrid_qid)

def delete_claim(session, factgrid_api_url, edit_token, claim_id):
    logging.info(f"Attempting to delete claim {claim_id} from FactGrid")
    if not DRY_RUN:
        r_del = session.post(factgrid_api_url, data={
            "action": "wbremoveclaims",
            "claim": claim_id,
            "token": edit_token,
            "format": "json"
        })
        result = r_del.json()
        if 'success' in result:
            logging.info("Removed %s", claim_id)
            return True
        else:
            logging.error("Failed to remove %s: %s", claim_id, result)
            return False
    logging.info("[DRY RUN] Would delete claim %s from FactGrid", claim_id)
    return True  # In dry run mode, we assume success without making changes

def set_factgrid_sitelink(session, factgrid_api_url, factgrid_qid, wikidata_qid, site_code, edit_token):
    check_params = {
        "action": "wbgetentities",
        "format": "json",
        "ids": factgrid_qid,
        "props": "sitelinks"
    }
    try:
        check_response = session.get(factgrid_api_url, params=check_params)
        check_response.raise_for_status()
        data = check_response.json()
        sitelinks = data.get("entities", {}).get(factgrid_qid, {}).get("sitelinks", {})
        if site_code in sitelinks:
            logging.info(f"Skipping {factgrid_qid} — sitelink for {site_code} already exists: {sitelinks[site_code]['title']}")
            return None
    except Exception as e:
        logging.error(f"Error checking sitelink for {factgrid_qid}: {e}")
        return None

    # If no sitelink exists, proceed to set it
    params = {
        "action": "wbsetsitelink",
        "format": "json",
        "id": factgrid_qid,
        "linksite": site_code,
        "linktitle": str(wikidata_qid),
        "token": edit_token
    }

    if DRY_RUN:
        logging.info(f"[DRY RUN] Would set sitelink for {factgrid_qid} to {wikidata_qid} on {site_code}")
        return None

    try:
        logging.info(f"Using params: {params}")
        response = session.post(factgrid_api_url, data=params)
        response.raise_for_status()
        time.sleep(1)  # avoid throttling
        logging.info(f"Set sitelink for {factgrid_qid} to {wikidata_qid} on {site_code}")
        return response.json()
    except session.exceptions.RequestException as e:
        logging.error(f"Error making request: {e}")
    except ValueError as e:
        logging.error(f"Error decoding JSON: {e}")
    return None

# Main function
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--post_qs', action='store_true', help='Post new sitelinks from qs file')
    parser.add_argument('--bib', type=str, default="BETA", help="Bibliography to use", choices=['BETA', 'BITECA', 'BITAGAP'])
    parser.add_argument('--instance', default='FACTGRID', choices=['PBCOG', 'FACTGRID'], help='Specify an instance from the list.  Default is FACTGRID.')
    parser.add_argument("--table", help="Table to process", choices=['analytic', 'biography', 'geography', 'institutions', 'library', 'subject', 'bibliography', 'copies', 'ms_ed', 'uniform_title'])
    parser.add_argument('--csv_file', type=str, help="csv file to process")
    parser.add_argument('--dry_run', action='store_true', help="Perform a dry run without making changes")
    parser.add_argument('--limit', type=int, help="Limit the number of entries to process")
    parser.add_argument('--delete_link', action='store_true', help="Delete existing P146 claims before setting new sitelinks")
    args = parser.parse_args()
    qs_file = f"{args.bib.lower()}_{args.instance.lower()}_{args.table}.qs"
    session, csrf_token = login()
    print(f"starting set_external_wikidata_link.py for {args.bib} {args.table}")
    logging.info(f"starting set_external_wikidata_link.py for {args.bib} {args.table}")
    global DRY_RUN
    DRY_RUN = args.dry_run
    global limit
    limit = args.limit if args.limit else None
    if args.post_qs:
        logging.info("Processing QS file: %s", qs_file)
        process_qs_file(session, csrf_token, qs_file)
    else:
        logging.info("Processing CSV file: %s", args.csv_file)
        process_query_csv(session, csrf_token, args.csv_file, delete_link=args.delete_link)

if __name__ == "__main__":
    main()
