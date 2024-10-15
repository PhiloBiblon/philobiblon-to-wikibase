import scp
from paramiko import SSHClient
from common.settings import BASE_IMPORT_OBJECTS
import datetime
import argparse

# Parse command line arguments for bibliography, table, and instance
bibliographies = ['beta', 'bitagap', 'biteca']
tables = ['analytic', 'biography', 'geography', 'institutions', 'library', 'subject', 'bibliography', 'copies', 'ms_ed', 'uniform_title']
instances = ['LOCAL_WB', 'PBSANDBOX', 'PBCOG', 'FACTGRID']
parser = argparse.ArgumentParser()
parser.add_argument('--bib', default='beta', choices=bibliographies, help='Specify a bibliography from the list.  Default is beta.')
parser.add_argument('--table', default='analytic', choices=tables, help='Specify a table from the list.  Default is analytic.')
parser.add_argument('--instance', default='PBCOG', choices=instances, help='Specify an instance from the list.  Default is PBCOG.')
args = parser.parse_args()
bib = args.bib.lower()
table = args.table.lower()
instance = args.instance.upper()

date = datetime.datetime.now().strftime('%Y-%m-%d')

# Define the local file path and the remote server details
file_name = f'{bib}_{table}'
local_file_path = f'../data/processed/pre/{bib}/{file_name}.csv'
remote_server = BASE_IMPORT_OBJECTS[instance]['SERVER']
print(remote_server)
remote_username = 'pi'
remote_command = f'openrefine-client --projectName={file_name}.{date} --create jason/{file_name}.csv'
private_key_path = '/Users/jhatfield/.ssh/id_rsa'

# Create an SSH client
ssh = SSHClient()
ssh.load_system_host_keys() # Requires local id_rsa key to be loaded on remote server
ssh.connect(hostname=remote_server, username=remote_username)

try:
  with scp.SCPClient(ssh.get_transport()) as client:
    client.put(local_file_path, f'~/jason/{file_name}.csv')
    print(f'File {file_name} uploaded to {remote_server}')
    print(f'Running command: {remote_command}')
    stdin, stdout, stderr = ssh.exec_command(remote_command)

    # Print the output of the command
    print(stdout.read().decode())
except Exception as e:
    print(f'An error occurred: {e}')
finally:
    # Close the SSH connection
    ssh.close()
    print(f'OR project {file_name} created and connection closed')
