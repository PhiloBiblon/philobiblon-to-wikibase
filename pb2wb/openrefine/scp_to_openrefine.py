import scp
from paramiko import SSHClient
from common.settings import BASE_IMPORT_OBJECTS
import datetime

# Define bibligraphy and other required variables
bib = 'beta'
table = 'bibliography'
instance = 'PBCOG'
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