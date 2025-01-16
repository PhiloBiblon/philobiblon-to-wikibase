import csv
import requests
from common.settings import BASE_IMPORT_OBJECTS
import time

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

def remove_qualifier_with_retry(session, csrf_token, claim_guid, property_qualifier, statement_details):
    """Removes a qualifier from a claim with retry on throttling."""
    try:
        claims = statement_details.get('claims', {}).get(PROPERTY, [])
        if claims:
            qualifiers = claims[0].get('qualifiers', {}).get(property_qualifier, [])
            if qualifiers:
                snak_hash = qualifiers[0].get('hash')
                if snak_hash:
                    response = remove_qualifiers(session, csrf_token, claim_guid, snak_hash)
                    if response and response.get("actionthrottledtext"):
                        print("Action throttled. Waiting for 30 seconds")
                        time.sleep(30)
                        response = remove_qualifiers(session, csrf_token, claim_guid, snak_hash)  # Retry
                    if response and not response.get("error"):
                        print(f'Success response: {response}')
                        print(f"Qualifier for {claim_guid} removed successfully")
                    elif response and response.get("error"):
                        print(f"Failed to remove qualifier for {claim_guid}: {response.get('error').get('info')}")
                    else:
                        print(f"Failed to get response for qualifier removal for {claim_guid}")
                else:
                    print(f"Snak hash not found for {claim_guid}")
            else:
                print(f"No {property_qualifier} qualifiers found for {claim_guid}")
        else:
            print(f"No claims found for {PROPERTY} and {claim_guid}")

    except Exception as e:
        print(f"An unexpected error occurred while removing qualifier for {claim_guid}")

# Process the CSV file
def process_csv(session, csrf_token):
    with open(CSV_FILE, mode='r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            item_id = row["item"].split("/")[-1]
            statement_uri = row["statement"]
            claim_guid = statement_uri.split("/")[-1]
            claim_guid = claim_guid.replace("-", "$", 1)

            print(f"Processing item: {item_id}, claim GUID: {claim_guid}")

            statement_details = fetch_statement_details(session, claim_guid)
            print("Statement details:", statement_details)

            remove_qualifier_with_retry(session, csrf_token, claim_guid, PROPERTY_QUALIFIER, statement_details)

    print(f'Processing {PROPERTY_QUALIFIER} deletes complete using {CSV_FILE}')

# Main function
def main():
    session, csrf_token = login()
    process_csv(session, csrf_token)

if __name__ == "__main__":
    main()