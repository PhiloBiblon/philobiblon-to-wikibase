import requests
from dotenv import load_dotenv
import os
import sys
import json
import subprocess
import argparse
from common.settings import OR_SERVER

RECONCILIATION =  {"PBCOG": {"service": "https://philobiblon.cog.berkeley.edu/reconcile/en/api",
                     "identifierSpace": "https://philobiblon.cog.berkeley.edu/entity/",
                     "schemaSpace": "https://philobiblon.cog.berkeley.edu/prop/direct/"},
                   "FACTGRID": {"service": "http://database.factgrid.de/reconcile/en/api",
                     "identifierSpace": "http://database.factgrid.de/entity/",
                     "schemaSpace": "https://database.factgrid.de/prop/direct/"}
}


def run_schema_update(project_name=None, project_id=None, instance='PBCOG'):
    print(f'using wikibase instance: {RECONCILIATION[instance] = }')
    # Gather credentials from .env file
    load_dotenv('open-refine.env') # .env file should be in the same directory as this script and contain admin username and password
    username = os.getenv("username")
    password = os.getenv("password")
    print(f'{username = } {password = }')
    auth = (username, password)

    or_server = OR_SERVER
    csrf_response = requests.get(or_server + '/command/core/get-csrf-token', auth=auth)
    csrf_token = csrf_response.json().get('token')

    print(f'{csrf_token = }')

    # Ensure csrf_token is not None
    if not csrf_token:
        raise ValueError("CSRF token could not be retrieved.")

    # Define the command to list projects
    command = 'openrefine-client -H philobiblon.cog.berkeley.edu -P 3333 --list'
    if not project_id:
        try:
            # Execute the project list command and capture output
            output = subprocess.run(command, check=True, capture_output=True, text=True, shell=True)  
            # Print the output
            print(output.stdout)
            output_list = output.stdout.split('\n')
            print(f'{output_list = }')
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")

        for item in output_list:
            if project_name in item:
                project_id = int(item.split(':')[0])
                print(f'{project_id = }')
                break
            else:
                print(f'Project {project_name} not found')

    # Add CSRF token to parameters
    post_params = {'csrf_token': csrf_token, 'project': f'{project_id}'}
    get_params = {'project': f'{project_id}'}

    # Gather columns with QNUMBER in the name
    get_response = requests.get(or_server + '/command/core/get-models', params=get_params, auth=auth)
    qnumber_columns = [col['name'] for col in get_response.json()['columnModel']['columns'] if 'QNUMBER' in col['name']]
    print(f'{qnumber_columns = }')

    # Apply operations to each column
    for column in qnumber_columns:
        print(f'processing column: {column = }')
        # Use the token in your POST request
        operations_array = [
        {
            "op": "core/recon-use-values-as-identifiers",
            "engineConfig": {
                "facets": [],
                "mode": "row-based"
            },
            "columnName": column,
            "service": RECONCILIATION[instance]["service"],
            "identifierSpace": RECONCILIATION[instance]["identifierSpace"],
            "schemaSpace": RECONCILIATION[instance]["schemaSpace"],
            "description": f'Use values as reconciliation identifiers in column {column}'
        }
    ]
        data = {
            'operations': json.dumps(operations_array)
        }
        print(f'{data = }')
        post_response = requests.post(or_server + '/command/core/apply-operations', params=post_params, data=data, auth=auth)

        # Print request details
        print("Request details:")
        print(f"Method: {post_response.request.method}")
        print(f"URL: {post_response.request.url}")
        print(f"Headers: {post_response.request.headers}")
        print(f"Body (if present): {post_response.request.body}")  # Might be empty or binary

        # Check for response and print output
        if post_response.status_code == 200:
            print(post_response.json())
        else:
            print(f"Error: {post_response.status_code}")
            print(post_response.text)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', type=str, help='Specify a project name to use')
    parser.add_argument('--id', type=int, help='Specify a project ID to use')
    parser.add_argument('--instance', default='PBCOG', choices=['PBCOG', 'FACTGRID'], help='Specify an instance from the list.  Default is PBCOG.')
    args = parser.parse_args()
    if args.project:
        run_schema_update(project_id=None, project_name=args.project, instance=args.instance)
    elif args.id:
        run_schema_update(project_id=args.id, project_name=None, instance=args.instance)
    else:
        print("Error: Please provide either a project name or ID.")
