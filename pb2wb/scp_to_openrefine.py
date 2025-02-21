import scp
import paramiko
from common.settings import BASE_IMPORT_OBJECTS
import datetime
import argparse
import getpass
from open_refine_schema import run_schema_update

# Parse command line arguments for bibliography, table, and instance
bibliographies = ['beta', 'bitagap', 'biteca']
tables = ['analytic', 'biography', 'geography', 'institutions', 'library', 'subject', 'bibliography', 'copies', 'ms_ed', 'uniform_title']
instances = ['LOCAL_WB', 'PBSANDBOX', 'PBCOG', 'FACTGRID']
parser = argparse.ArgumentParser()
parser.add_argument('--bib', default='beta', choices=bibliographies, help='Specify a bibliography from the list.  Default is beta.')
parser.add_argument('--table', default='analytic', choices=tables, help='Specify a table from the list.  Default is analytic.')
parser.add_argument('--instance', default='PBCOG', choices=instances, help='Specify an instance from the list.  Default is PBCOG.')
parser.add_argument('--schema', help='Perform schema update, including arg performs schema update', action='store_true')
parser.add_argument('--identity_file', help='identity file')
parser.add_argument('--alt_csv', help='alternate csv file')
args = parser.parse_args()
bib = args.bib.lower()
table = args.table.lower()
instance = args.instance.upper()
alt_csv = args.alt_csv
schema = args.schema

date = datetime.datetime.now().strftime('%Y-%m-%d')

# Get the current username
username = getpass.getuser()
print(f"Current username: {username}")

# Define the local file path and the remote server details
file_name = f'{instance.lower()}_{bib}_{table}'
local_file_path = f'../data/processed/pre/{bib}/{file_name}.csv'
if alt_csv:
    local_file_path = alt_csv
    file_name = alt_csv.split('/')[-1].split('.')[0]
remote_server = BASE_IMPORT_OBJECTS[instance]['SERVER']
print(f'using remote server: {remote_server}')
remote_username = BASE_IMPORT_OBJECTS[instance]['SSH_USER']
print(f"{remote_username = }")
remote_command = f'openrefine-client --projectName={file_name}.{date} --create jason/{file_name}.csv'
private_key_path = args.identity_file or f'/Users/{username}/.ssh/id_rsa'

# Create an SSH client
ssh = paramiko.SSHClient()
ssh.load_system_host_keys() # Requires local id_rsa key to be loaded on remote server
print(f"{private_key_path = }")
private_key = paramiko.RSAKey.from_private_key_file(private_key_path)
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(
    hostname=remote_server,
    username=remote_username,
    pkey=private_key
)


# Check if connection is established
if ssh.get_transport() is None:
    raise ConnectionError("Failed to connect to remote server.")

try:
  with scp.SCPClient(ssh.get_transport()) as client:
    client.put(local_file_path, f'~/jason/{file_name}.csv')
    print(f'File {file_name} uploaded to {remote_server}')
    print(f'Running command: {remote_command}')
    stdin, stdout, stderr = ssh.exec_command(remote_command)

    # Print the output of the command
    output = stdout.read().decode()
    print(output)

    output_list = output.split('\n')
    print(f'{output_list = }')

    for line in output_list:
        if "id:" in line:
            project_id = line.split(":")[1].strip()
            print(f"Extracted project ID: {project_id}")
            break

except (ConnectionError, paramiko.SSHException) as e:
    print(f'An error occurred: {e}')
finally:
    # Close the SSH connection
    if ssh is not None or ssh.get_transport() is not None:
        ssh.close()
    print(f'OR project {file_name} created and connection closed')

# Run the schema update
if schema:
    print(f'Running schema update for {file_name}')
    run_schema_update(project_id=project_id, project_name=None, instance=instance)
