import os
import subprocess
import time
import datetime
import json

bibliography = 'BETA' # 'BETA' 'BITECA' 'BITAGAP'
tablename = 'analytic' # 'geography' 'analytic' 'library' 'ms_ed' 'biographies' 'copies' 'institutions' 'subject' 'uniform_title'
date = datetime.datetime.now().strftime("%Y%m%d_%H%M")
path = '/Users/jhatfield/work/philobiblon-to-wikibase/pb2wb/qs_files'
url = "https://philobiblon.cog.berkeley.edu/qs/api.php"
username = 'Jason_Hatfield'
batchname = f'{bibliography}_{tablename}_{date}'
token = '$2y$10$tRG3uDQ4rwWQUhopmhxUOuKJYIyAUbvB0aEWf8qoiiGeMpadsVace'

def get_batch_status(batch_id):
    batch_status_command = f"curl {url} -d action=get_batch_info -d batch={batch_id}"
    batch_status = subprocess.run(batch_status_command, capture_output=True, text=True, shell=True)
    try:
        data = json.loads(batch_status.stdout)
        batch_status = data["data"][str(batch_id)]["batch"]["status"]
    except json.JSONDecodeError:
        print("Error parsing JSON output:", batch_status.stdout)
    return batch_status

for filename in os.listdir(path):
    print(filename)
    file_path = os.path.join(path, filename)
    if os.path.isfile(file_path) and tablename in filename:
        response = get_batch_status(batchname)
        curl_command = f"curl {url} -d action=import -d submit=1 -d format=v1 -d username={username} -d batchname={batchname} --data-raw token=\'{token}\' --data-urlencode data@{file_path}"
        print(curl_command)
        post_qs = subprocess.run(curl_command, capture_output=True, text=True, shell=True)
        if post_qs.returncode != 0:
            print("Error executing curl command:", post_qs.stderr)
            exit(1)
        try:
            data = json.loads(post_qs.stdout)
            batch_id = data["batch_id"]
        except json.JSONDecodeError:
            print("Error parsing JSON output:", post_qs.stdout)
        status = get_batch_status(batch_id)
        while status == "INIT" or status == "RUNNING":
            print(f'Batch import {batch_id} still running, sleeping for 10 minutes')
            time.sleep(600)
            print("Checking batch status")
            status = get_batch_status(batch_id)
        print(f'Batch import {batch_id} complete with status {status}')