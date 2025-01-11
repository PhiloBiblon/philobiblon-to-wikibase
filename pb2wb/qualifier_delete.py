import csv
import requests
from common.settings import BASE_IMPORT_OBJECTS

# Example SPARQL query to fetch items with P2 statements qualified by P3
'''
SELECT ?item ?statement ?type ?typeLabel ?p3Value ?p3ValueLabel ?pbid
WHERE {
  ?item p:P2 ?statement.                      # Match P2 statements
  ?statement ps:P2 ?type.                     # Extract the main value of P2
  ?statement pq:P3 ?p3Value.                  # Ensure P2 is qualified by P3 and get the qualifier value
  ?item wdt:P476 ?pbid                        # We're only interested in objects that have a pbid
  
  FILTER CONTAINS(STR(?pbid), "BETA geoid")   # We're only interested in BETA geo objects for now
  SERVICE wikibase:label { 
    bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". 
  }
}
'''

# Configuration
wb = 'FACTGRID' # 'PBCOG' or 'FACTGRID'
API_URL = "https://database.factgrid.de/w/api.php"
user = BASE_IMPORT_OBJECTS[f'{wb}']['WB_USER']
password = BASE_IMPORT_OBJECTS[f'{wb}']['WB_PASSWORD']
PROPERTY = "P2"  # The property to be checked for qualifiers
PROPERTY_QUALIFIER = "P3"  # The qualifier property to be removed
CSV_FILE = "beta_fg_p3_deletes.csv"  # The CSV file containing the items and statements to be processed

# Authenticate
def login():
    session = requests.Session()
    login_token = session.get(API_URL, params={"action": "query", "meta": "tokens", "type": "login", "format": "json"}).json()['query']['tokens']['logintoken']
    session.post(API_URL, data={"action": "login", "lgname": user, "lgpassword": password, "lgtoken": login_token, "format": "json"})
    csrf_token = session.get(API_URL, params={"action": "query", "meta": "tokens", "format": "json"}).json()['query']['tokens']['csrftoken']
    print(f"CSRF Token: {csrf_token}")
    return session, csrf_token

# Fetch the full statement details to see qualifiers
def fetch_statement_details(session, statement_guid):
    response = session.get(API_URL, params={
        "action": "wbgetclaims",
        "claim": statement_guid,
        "format": "json"
    })
    return response.json()

# Remove Qualifiers using snak hash
def remove_qualifiers(session, csrf_token, claim_guid, qualifier_snak_hash):
    response = session.post(API_URL, data={
        "action": "wbremovequalifiers",
        "claim": claim_guid,  # Use the claim GUID
        "qualifiers": qualifier_snak_hash, # Pass the snak hash for the P3 qualifier
        "token": csrf_token,
        "format": "json"
    })
    return response.json()

# Process the CSV file
def process_csv(session, csrf_token):
    with open(CSV_FILE, mode='r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            item_id = row["item"].split("/")[-1]  # Extract Q-number from the URI
            statement_uri = row["statement"]  # Full URI for the statement
            claim_guid = statement_uri.split("/")[-1]  # Extract the GUID from the URI
            
            # Correct the GUID format by replacing the '-' with '$'
            claim_guid = claim_guid.replace("-", "$", 1)  # Only replace the first '-' (between item ID and GUID part)
            
            print(f"Processing item: {item_id}, claim GUID: {claim_guid}")

            # Fetch statement details to check the actual qualifiers
            statement_details = fetch_statement_details(session, claim_guid)
            print("Statement details:", statement_details)

            # Extract the snak hash for P3 qualifier
            try:
                snak_hash = statement_details['claims'][PROPERTY][0]['qualifiers'][PROPERTY_QUALIFIER][0]['hash']
                print(f"Snak hash for qualifier: {snak_hash}")
            except KeyError:
                snak_hash = None
                print(f"No qualifiers found for {claim_guid}")

            # Attempt to remove the P3 qualifier using the snak hash
            if snak_hash is not None:
                try:
                    response = remove_qualifiers(session, csrf_token, claim_guid, snak_hash)
                    print("Remove qualifier response:", response)
                except Exception as e:
                    print(f"Failed to remove qualifier for {claim_guid}: {e}")
        
    print(f'Processing {PROPERTY_QUALIFIER} deletes complete using {CSV_FILE}')

# Main function
def main():
    session, csrf_token = login()
    process_csv(session, csrf_token)

if __name__ == "__main__":
    main()