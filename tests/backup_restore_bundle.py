import json
import os
from kubernetes import client,config
from kubernetes.stream import stream
import requests
import urllib3
import time
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


current_directory = os.getcwd()
with open(current_directory+"/vars.json")  as f:
    data_json = json.load(f)
    
# Initialize variables
VIP = data_json["VIP"]
robin_user = data_json["ROBIN_USER"]
robin_passwd = data_json["ROBIN_PASSWD"]
tenant = "Administrators"
port = 29442
appName = data_json["appName"]
ns = data_json["ns"]
# bundleid = data_json["bundleid"]
rpool = data_json["rpool"]
repo = data_json["repo"]
remote_file_path = data_json["remote_file_path"]
minio = data_json["minio"]
server_url = f"https://{VIP}:{port}"


def robin_login():
    try:
        ip_url = f"https://{VIP}:"
        login_url = ip_url + str(port) + "/api/v3/robin_server/login"
        robin_obj = requests.post(login_url, json={'password': robin_passwd, 'username': robin_user, 'tenant': tenant},
                                  verify=False,
                                  headers={'Content-type': 'application/json'})
        res_obj = robin_obj.json()
        auth_token = res_obj["token"]
        list = [res_obj,auth_token,robin_obj.status_code]
        return list
    except Exception:
        raise

# method to create robin namespace
def robin_namespace(auth_token):
    try:
        file_header = {'Authorization': auth_token, 'Content-type': 'application/json'}
        url = server_url + "/api/v3/robin_server/namespaces"
        params_obj = {'name': ns}
        response_obj = requests.post(url, data=json.dumps(params_obj), verify=False, headers=file_header)
        response = response_obj.status_code
        if response == 400:
            return 200
        else:
            return response
    except Exception:
        raise

# method to create app from existing bundle
def create_app_from_bundle(auth_token,bundleid):
    try:
        file_header = {'Authorization': auth_token, 'Content-type': 'application/json'}
        url = server_url + "/api/v3/robin_server/apps"
        params_obj = {'kind':'ROBIN','name':appName,'namespace':ns,"template_json":{"roles":[]},'bundleid':bundleid,'rpool': rpool}
        response_obj = requests.post(url, data=json.dumps(params_obj), verify=False, headers=file_header)
        if response_obj and response_obj.status_code  == 202:
            data = response_obj.json()
            jobid = str(data["jobid"])
            get_url = server_url + "/api/v5/robin_server/jobs/" + jobid
            while True:
                get_resp = requests.get(get_url, verify=False, headers=file_header)
                job_details = get_resp.json()["job"][0]
                if job_details["state"] == 10 and job_details['error'] == 0 and get_resp.status_code == 200:
                    break
            response = [response_obj.json(),response_obj.status_code]
            return response
        elif response_obj.status_code  == 409:
            response = ["app with "+appName+" already exists",202]
            return response
        else:
            raise Exception("Unable to create app",response_obj.json(),response_obj.status_code)
    except Exception:
        raise

# Method to register external repo
def register_external_repo(auth_token):
    try:
        file_header = {'Authorization': auth_token, 'Content-type': 'application/json'}
        url = server_url + "/api/v3/robin_server/storage_repo"
        params_obj = minio
        response_obj = requests.post(url, data=json.dumps(params_obj), verify=False, headers=file_header)
        if response_obj and response_obj.status_code == 202:
            data = response_obj.json()
            jobid = str(data["jobid"])
            get_url = server_url + "/api/v5/robin_server/jobs/" + jobid
            while True:
                get_resp = requests.get(get_url, verify=False, headers=file_header)
                job_details = get_resp.json()["job"][0]
                if job_details["state"] == 10 and job_details['error'] == 0 and get_resp.status_code == 200:
                    break
            response = [response_obj.json(),response_obj.status_code]
            return response
        else:
            raise Exception("register failed",response_obj.json(),response_obj.status_code)
    except Exception:
        raise

# method to attach app to external repo
def attach_app_to_ext_repo(auth_token):
    try:
        file_header = {'Authorization': auth_token, 'Content-type': 'application/json'}
        url = server_url + "/api/v3/robin_server/apps/" + appName
        params_obj = {"action":"add_repo","name":appName,"repo_name":repo}
        response_obj = requests.put(url, data=json.dumps(params_obj), verify=False, headers=file_header)
        if response_obj and response_obj.status_code == 202:
            data = response_obj.json()
            jobid = str(data["jobid"])
            get_url = server_url + "/api/v5/robin_server/jobs/" + jobid
            while True:
                get_resp = requests.get(get_url, verify=False, headers=file_header)
                job_details = get_resp.json()["job"][0]
                if job_details["state"] == 10 and job_details['error'] == 0 and get_resp.status_code == 200:
                    break
            response = [response_obj.json(),response_obj.status_code]
            return response
        else:
            raise Exception("register failed", response_obj.json(), response_obj.status_code)
    except Exception:
        raise

# Get pod name
def get_pod_name(kubeconfig_path):
    try:
        config.load_kube_config(kubeconfig_path)
        # Create Kubernetes API client
        api_instance = client.CoreV1Api()

        api_response = api_instance.list_namespaced_pod(namespace=ns,label_selector="app="+appName)
        for pod in api_response.items:
            pod_name = pod.metadata.name
        return pod_name
    except Exception:
        raise("Unable to fetch pod details",api_response.items)


#upload file to pod
def upload_file_to_pod(kubeconfig_path):
    try:
        podname = get_pod_name(kubeconfig_path)
        local_file_path = 'demofile.txt'

        with open(local_file_path, "w") as f:
            f.write("Now the file has more content!")

        # Load kubeconfig_path
        config.load_kube_config(kubeconfig_path)

        # Read the file content
        with open(local_file_path, 'rb') as file:
            file_content = file.read()
        # Define the command to create the file in the pod
        exec_command = [
            'sh',
            '-c',
            f'cat > {remote_file_path}'
        ]

        # Create an API client
        api_instance = client.CoreV1Api()
        # Execute the command in the pod
        resp = stream(api_instance.connect_get_namespaced_pod_exec,
                      name=podname,
                      namespace=ns,
                      container=podname,
                      command=exec_command,
                      stderr=True, stdin=True,
                      stdout=True, tty=False, _preload_content=False)
        # Send the file content to the pod
        resp.write_stdin(file_content)
        resp.close()
        # os.remove(local_file_path)
    except Exception:
        raise

def backup_creation(auth_token):
    try:
        file_header = {'Authorization': auth_token, 'Content-type': 'application/json'}
        url = server_url + "/api/v3/robin_server/apps"
        # snapshotid = get_snapshot_id(server_url,auth_token)
        params_obj = {"action":"backup","app_name":appName,"repo":repo}
        response_obj = requests.put(url, data=json.dumps(params_obj), verify=False, headers=file_header)

        # Get the response code
        response_code = response_obj.status_code
        if response_obj and response_code == 202:
            data = response_obj.json()
            jobid = str(data["jobid"])
            get_url = server_url + "/api/v5/robin_server/jobs/" + jobid
            while True:
                get_resp = requests.get(get_url, verify=False, headers=file_header)
                job_details = get_resp.json()["job"][0]
                if job_details["state"] == 10 and job_details['error'] == 0 and get_resp.status_code == 200:
                    break
            response = [response_obj.json(), response_obj.status_code]
            return response
        else:
            raise Exception("Unable to create backup",response_obj.json(), response_obj.status_code)
    except Exception:
        raise

# method to delete app
def delete_app(auth_token):
    try:
        file_header = {'Authorization': auth_token}
        get_url = server_url + "/api/v6/robin_server/apps/"+appName+"?itermap=true"
        get_resp = requests.get(get_url,verify=False, headers=file_header)
        snapname = get_resp.json()["delete_order"][0][0]
        snap_del_url = server_url + "/api/v6/robin_server/apps/"+snapname+"?objtype=snapshot"
        requests.delete(snap_del_url,verify=False,headers=file_header)
        time.sleep(10)
        url = server_url + "/api/v6/robin_server/apps/"+appName
        response_obj = requests.delete(url,verify=False, headers=file_header)

        # Get the response code
        response_code = response_obj.status_code
        if response_obj and response_code == 202:
            data = response_obj.json()
            jobid = str(data["jobid"])
            get_url = server_url + "/api/v5/robin_server/jobs/" + jobid
            while True:
                get_resp = requests.get(get_url, verify=False, headers=file_header)
                job_details = get_resp.json()["job"][0]
                if job_details["state"] == 10 and job_details['error'] == 0 and get_resp.status_code == 200:
                    break
            response = [response_obj.json(), response_obj.status_code]
            return response
        else:
            raise Exception(response_obj.json(), response_obj.status_code)
    except Exception:
        raise


# method to get backup id
def fetch_backup_id(auth_token):
    try:
        backupid_list = []
        file_header = {'Authorization': auth_token}
        url = server_url + "/api/v6/robin_server/backups"
        response_obj = requests.get(url, verify=False, headers=file_header)

        # Get the response code
        response_code = response_obj.status_code
        if response_obj and response_code == 200:
            data = response_obj.json()
            backupid = 0
            for item in data["items"]:
                if item["state"] == "Pushed":
                    backupid = item["id"]
                    backupid_list.append(backupid)
            return [str(backupid), response_obj.status_code,backupid_list]
        else:
            raise Exception("Unable to fetch backup id",response_obj.json(), response_obj.status_code)
    except Exception:
        raise

# method to restore app from backup
def app_restore_from_backup(auth_token):
    try:
        file_header = {'Authorization': auth_token}
        backupid = fetch_backup_id(auth_token)
        if backupid[0] == 0:
            raise Exception("Backup Id is invalid")
        get_url = server_url + "/api/v3/robin_server/storage_repo?sub-command=get-backup-info&backupid="+backupid[0]+""
        resp = requests.get(get_url, verify=False, headers=file_header)
        data = resp.json()
        for item in data['data']:
            configs = item["config"]
        configs["name"] = appName
        configs["repo_name"] = repo
        configs["namespace"] = ns
        url = server_url + "/api/v3/robin_server/apps"
        response_obj = requests.post(url, data=json.dumps(configs), verify=False, headers=file_header)

        # Get the response code
        response_code = response_obj.status_code
        if response_obj and response_code == 202:
            data = response_obj.json()
            jobid = str(data["jobid"])
            get_url = server_url + "/api/v5/robin_server/jobs/" + jobid
            while True:
                get_resp = requests.get(get_url, verify=False, headers=file_header)
                job_details = get_resp.json()["job"][0]
                if job_details["state"] == 10 and job_details['error'] == 0 and get_resp.status_code == 200:
                    break
            response = [response_obj.json(), response_obj.status_code]
            return response
        else:
            print(response_code, response_obj)
            raise Exception("Unable to restore app from backup",response_obj.json(), response_obj.status_code)
    except Exception:
        raise


# method to list file from pod
def list_file_from_pod(kubeconfig_path):
    try:
        pod_name = get_pod_name(kubeconfig_path)

        # Load kubeconfig_path
        config.load_kube_config(kubeconfig_path)

        # Define the command to create the file in the pod
        exec_command = ['cat', remote_file_path]

        # Create an API client
        api_instance = client.CoreV1Api()

        # Execute the command in the pod
        resp = stream(api_instance.connect_get_namespaced_pod_exec,
                      name=pod_name,
                      namespace=ns,
                      container=pod_name,
                      command=exec_command,
                      stderr=True, stdin=True,
                      stdout=True, tty=False)

        with open("demofile.txt", 'r') as file:
            file_content = file.read()

        if file_content == resp:
            return 202
        else:
            raise Exception(" Unable to verify restore",resp)
    except Exception:
        raise

def delete_backups(auth_token):
    try:
        backupid_list = fetch_backup_id(auth_token)
        file_header = {'Authorization': auth_token}

        url = server_url + "/api/v3/robin_server/backups"
        for id in backupid_list[2]:
            params_obj = {"action":"purge","backupid":id}
            response_obj = requests.delete(url,data=json.dumps(params_obj),verify=False, headers=file_header)
            response_code = response_obj.status_code
            if response_obj and response_code == 202:
                data = response_obj.json()
                jobid = str(data["jobid"])
                get_url = server_url + "/api/v5/robin_server/jobs/" + jobid
                while True:
                    get_resp = requests.get(get_url, verify=False, headers=file_header)
                    job_details = get_resp.json()["job"][0]
                    if job_details["state"] == 10 and job_details['error'] == 0 and get_resp.status_code == 200:
                        break
                response = [response_obj.json(), response_obj.status_code]
                return response
            else:
                print(response_code, response_obj)
                raise Exception("Unable to delete backup", response_obj.json(), response_obj.status_code)
    except Exception:
        raise

def delete_ext_repo(auth_token):
    try:
        file_header = {'Authorization': auth_token, 'Content-type': 'application/json'}
        url = server_url + "/api/v3/robin_server/storage_repo/"+repo
        params_obj = {"force": "true"}
        response_obj = requests.delete(url, data=json.dumps(params_obj), verify=False, headers=file_header)
        if response_obj and response_obj.status_code == 202:
            data = response_obj.json()
            jobid = str(data["jobid"])
            get_url = server_url + "/api/v5/robin_server/jobs/" + jobid
            while True:
                get_resp = requests.get(get_url, verify=False, headers=file_header)
                job_details = get_resp.json()["job"][0]
                if job_details["state"] == 10 and job_details['error'] == 0 and get_resp.status_code == 200:
                    break
            response = [response_obj.json(), response_obj.status_code]
            return response
        else:
            raise Exception(response_obj.json(), response_obj.status_code)
    except Exception:
        raise