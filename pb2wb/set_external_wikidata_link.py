import requests
import pandas as pd
from common.settings import BASE_IMPORT_OBJECTS

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
#CSV_FILE = "p146_to_sitelink.csv"  # The CSV file containing the P146 items to be processed
CSV_FILE = "p146_to_sitelink_1row.csv"  # The CSV file containing the P146 items to be processed
factgrid_api_url = "https://database.factgrid.de/w/api.php"  # Replace with your FactGrid API URL
site_code = "wikidatawiki" #This is the common site code for wikidata


# Authenticate
def login():
    session = requests.Session()
    login_token = session.get(factgrid_api_url, params={"action": "query", "meta": "tokens", "type": "login", "format": "json"}).json()['query']['tokens']['logintoken']
    session.post(factgrid_api_url, data={"action": "login", "lgname": user, "lgpassword": password, "lgtoken": login_token, "format": "json"})
    csrf_token = session.get(factgrid_api_url, params={"action": "query", "meta": "tokens", "format": "json"}).json()['query']['tokens']['csrftoken']
    print(f"CSRF Token: {csrf_token}")
    return session, csrf_token

def process_csv(session, csrf_token):
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
        return response.json()
    except session.exceptions.RequestException as e:
        print(f"Error making request: {e}")
        return None
    except ValueError as e:
        print(f"Error decoding JSON: {e}")
        return None


# Main function
def main():
    session, csrf_token = login()
    process_csv(session, csrf_token)

if __name__ == "__main__":
    main()
