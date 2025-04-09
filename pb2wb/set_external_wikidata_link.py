import requests
import pandas as pd
from common.settings import BASE_IMPORT_OBJECTS
import time
import argparse

# Example SPARQL query to fetch items with P146 statements and wikidata.org in the value
'''
SELECT ?item ?pbid ?online_info ?link
WHERE {
  ?item wdt:P476 ?pbid .
  ?item wdt:P146 ?online_info .
  FILTER (CONTAINS(STR(?online_info), "wikidata.org")) # Filter for "wikidata.org" in P146 value
  OPTIONAL { ?link schema:about ?item ; schema:isPartOf <https://www.wikidata.org/> . }
  FILTER ( !bound(?link) || STR(?link) != STR(?online_info) )  # Check for mismatch
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
    session.post(factgrid_api_url, data={"action": "login", "lgname": user, "lgpassword": password, "lgtoken": login_token, "format": "json"})
    csrf_token = session.get(factgrid_api_url, params={"action": "query", "meta": "tokens", "format": "json"}).json()['query']['tokens']['csrftoken']
    print(f"CSRF Token: {csrf_token}")
    return session, csrf_token

def process_query_csv(session, csrf_token):
    # Load the CSV file into a DataFrame
    df = pd.read_csv(CSV_FILE, names=['item', 'pbid', 'online_info', 'link'])

    # Extract the Q numbers from the URLs
    df['item'] = df['item'].str.extract(r'(Q\d+)', expand=False)
    df['online_info'] = df['online_info'].str.extract(r'(Q\d+)', expand=False)
    df['link'] = df['link'].str.extract(r'(Q\d+)', expand=False)

    # Condition 1: Rows where `online_info` exists but `link` does not exist
    df_no_link = df[df['online_info'].notna() & df['link'].isna()]
    print("Rows where 'online_info' exists but 'link' does not:")
    print(df_no_link)
    # Iterate over the rows and set the sitelinks
    for _, row in df_no_link.iterrows():
        factgrid_qid = row['item']
        wikidata_qid = row['online_info']
        print(f"FactGrid QID: {factgrid_qid}, Wikidata QID: {wikidata_qid}")
        response = set_factgrid_sitelink(session, factgrid_api_url, factgrid_qid, wikidata_qid, site_code, csrf_token)
        if response:
            print(response)
        else:
            print("Failed to set sitelink.")

    # Condition 2: Rows where both `online_info` and `link` exist but do not match
    df_mismatches = df[df['online_info'].notna() & df['link'].notna() & (df['online_info'] != df['link'])]
    # Remove duplicates by `item`, keeping the first occurrence
    df_mismatches = df_mismatches.drop_duplicates(subset='item')
    print("\nRows where both 'online_info' and 'link' exist but do not match:")
    print(df_mismatches)

def process_qs_file(session, csrf_token, qs_file):
    print(f"Processing QS file: {qs_file}")
    with open(qs_file, 'r') as f:
        lines = f.readlines()
    for line in lines:
        line = line.split("\t")
        if line[1] == 'P146' and len(line) >= 3 and "wikidata.org/wiki/Q" in line[2]:
            print(f"Processing line: {line}")
            item = line[0].split('/')[-1]
            online_info = line[2].strip('"').split('/')[-1]
            print(f"FactGrid QID: {item}, Wikidata QID: {online_info}")
            response = set_factgrid_sitelink(session, factgrid_api_url, item, online_info, site_code, csrf_token)
            if response:
                print(response)
            else:
                print("Failed to set sitelink.")

def set_factgrid_sitelink(session, factgrid_api_url, factgrid_qid, wikidata_qid, site_code, edit_token):
    params = {
        "action": "wbsetsitelink",
        "format": "json",
        "id": factgrid_qid,
        "linksite": site_code,
        "linktitle": f"{wikidata_qid}",
        "token": edit_token
    }

    try:
        print(f'Using params: {params}')
        response = session.post(factgrid_api_url, data=params)
        response.raise_for_status()
        time.sleep(1)  # Sleep for 1 second to avoid throttling
        return response.json()
    except session.exceptions.RequestException as e:
        print(f"Error making request: {e}")
        return None
    except ValueError as e:
        print(f"Error decoding JSON: {e}")
        return None


# Main function
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--post_qs', action='store_true', help='Post new sitelinks from qs file')
    parser.add_argument('--bib', type=str, default="BETA", help="Bibliography to use", choices=['BETA', 'BITECA', 'BITAGAP'])
    parser.add_argument('--instance', default='FACTGRID', choices=['PBCOG', 'FACTGRID'], help='Specify an instance from the list.  Default is FACTGRID.')
    parser.add_argument("--table", help="Table to process", choices=['analytic', 'biography', 'geography', 'institutions', 'library', 'subject', 'bibliography', 'copies', 'ms_ed', 'uniform_title'])
    parser.add_argument('--csv_file', type=str, help="csv file to process")
    args = parser.parse_args()
    qs_file = f"{args.bib.lower()}_{args.instance.lower()}_{args.table}.qs"
    session, csrf_token = login()
    if args.post_qs:
        print(f"Processing QS file: {qs_file}")
        process_qs_file(session, csrf_token, qs_file)
    else:
        process_query_csv(session, csrf_token, args.csv_file)

if __name__ == "__main__":
    main()
