import requests
from dotenv import load_dotenv
import os
import json

load_dotenv('open-refine.env')

username = os.getenv("username")
password = os.getenv("password")

print(f'{username = } {password = }')

auth = (username, password)

or_server = 'https://philobiblon.cog.berkeley.edu/openrefine'
csrf_response = requests.get(or_server + '/command/core/get-csrf-token', auth=auth)
csrf_token = csrf_response.json().get('token')

print(f'{csrf_token = }')

# Ensure csrf_token is not None
if not csrf_token:
    raise ValueError("CSRF token could not be retrieved.")

# operations_array = [
#     {
#         "op": "core/column-addition",
#         "description": "Add column test",
#         "engineConfig": {
#             "facets": [],
#             "mode": "row-based"
#         },
#         "newColumnName": "new_column",
#         "columnInsertIndex": 0,
#         "baseColumnName": "TEXT_MANID_QNUMBER",
#         "expression": "grel:value",
#         "onError": "keep-original"
#     }
# ]

operations_array = [
    {
        "op": "core/recon-use-values-as-identifiers",
        "engineConfig": {
            "facets": [],
            "mode": "row-based"
        },
        "columnName": "MANID_QNUMBER",
        "service": "https://philobiblon.cog.berkeley.edu/reconcile/en/api",
        "identifierSpace": "https://philobiblon.cog.berkeley.edu/entity/",
        "schemaSpace": "https://philobiblon.cog.berkeley.edu/prop/direct/",
        "description": "Use values as reconciliation identifiers in column MANID_QNUMBER"
    }
]

# Add CSRF token to parameters
params = {'csrf_token': csrf_token, 'project': '2284302640480'}

# Use the token in your POST request
data = {
    'operations': json.dumps(operations_array)
}

response = requests.post(or_server + '/command/core/apply-operations', params=params, data=data, auth=auth)


print("Request details:")
print(f"Method: {response.request.method}")
print(f"URL: {response.request.url}")
print(f"Headers: {response.request.headers}")
print(f"Body (if present): {response.request.body}")  # Might be empty or binary

# Check for response and print output
if response.status_code == 200:
    print(response.json())
else:
    print(f"Error: {response.status_code}")
    print(response.text)
