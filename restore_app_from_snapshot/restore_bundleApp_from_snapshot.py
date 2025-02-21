import json
from kubernetes import client,config
from kubernetes.stream import stream
import requests
import urllib3
import time
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


with open('vars.json') as f:
    data_json = json.load(f)
    # variables
VIP = data_json["VIP"]
robin_user = data_json["ROBIN_USER"]
robin_passwd = data_json["ROBIN_PASSWD"]
tenant = "Administrators"
port = 29442
appName = data_json["appName"]
snapName = data_json["snapName"]
ns = data_json["ns"]
bundleid = data_json["bundleid"]
rpool = data_json["rpool"]
repo = data_json["repo"]
remote_file_path = data_json["remote_file_path"]
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
def create_app_from_bundle(auth_token):
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
        else:
            raise Exception("Unable to create app",response_obj.json(),response_obj.status_code)
    except Exception:
        raise

def get_pod_name():
    try:
        config.load_kube_config("kubeconfig")
        # Create Kubernetes API client
        api_instance = client.CoreV1Api()

        api_response = api_instance.list_namespaced_pod(namespace=ns,label_selector="app="+appName)
        for pod in api_response.items:
            pod_name = pod.metadata.name
        return pod_name
    except Exception:
        raise("Unable to fetch pod details",api_response.items)


#upload file to pod
def upload_file_to_pod():
    try:
        podname = get_pod_name()
        local_file_path = 'demofile.txt'

        with open(local_file_path, "w") as f:
            f.write("Now the file has more content!")

        # Load kubeconfig
        config.load_kube_config("kubeconfig")

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

def create_snapshot(auth_token):
    try:
        file_header = {'Authorization': auth_token, 'Content-type': 'application/json'}
        url = server_url + "/api/v3/robin_server/apps/"+appName
        params_obj = {"action":"snapshot","snapname":snapName,"namespace":ns}
        response_obj = requests.put(url, data=json.dumps(params_obj), verify=False, headers=file_header)
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
        else:
            raise Exception("Unable to create snapshot",response_obj.json(),response_obj.status_code)
    except Exception:
        raise

def delete_data_from_pod():
    try:
        podname = get_pod_name()
        local_file_path = 'demofile.txt'

        with open(local_file_path, "w") as f:
            f.write("Now the file has more content!")

        config.load_kube_config("kubeconfig")

        # Define the command to delete the file in the pod
        exec_command = [
            'sh',
            '-c',
            f'rm -rf  {remote_file_path}'
        ]
        api_instance = client.CoreV1Api()
        # Execute the command in the pod
        stream(api_instance.connect_get_namespaced_pod_exec,
                      name=podname,
                      namespace=ns,
                      container=podname,
                      command=exec_command,
                      stderr=True, stdin=True,
                      stdout=True, tty=False)

    except Exception:
        raise

def fetch_snapshot_id(auth_token):
    try:
        file_header = {'Authorization': auth_token, 'Content-type': 'application/json'}
        url = server_url + "/api/v6/robin_server/appsview?akind=robin&parentapp="+appName+"&atype=SNAPSHOT&namespace="+ns
        response_obj = requests.get(url, verify=False, headers=file_header)
        if response_obj and response_obj.status_code == 200:
            data = response_obj.json()
            for item in data["robin"]["apps"]:
                return item["unique_id"],response_obj.status_code
        else:
            raise Exception("unable to fetch snapshot id",response_obj.status_code,response_obj.json())
    except Exception:
        raise


def restore_app_from_snapshot(auth_token):
    try:
        snapshotid = fetch_snapshot_id(auth_token)
        file_header = {'Authorization': auth_token, 'Content-type': 'application/json'}
        url = server_url + "/api/v3/robin_server/apps/" + appName
        params_obj = {"action":"rollback","snapshotid":snapshotid[0]}
        response_obj = requests.put(url, data=json.dumps(params_obj), verify=False, headers=file_header)
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
        else:
            raise Exception("Unable to restore app from snapshot",response_obj.json(),response_obj.status_code)
    except Exception:
        raise

def verify_data_restore():
    try:
        podname = get_pod_name()

        with open("demofile.txt", 'r') as file:
            file_content = file.read()

        config.load_kube_config("kubeconfig")
        # Define the command to delete the file in the pod
        exec_command = [
            'sh',
            '-c',
            f'cat  {remote_file_path}'
        ]
        api_instance = client.CoreV1Api()
        # Execute the command in the pod
        resp = stream(api_instance.connect_get_namespaced_pod_exec,
                      name=podname,
                      namespace=ns,
                      container=podname,
                      command=exec_command,
                      stderr=True, stdin=True,
                      stdout=True, tty=False)

        if file_content == resp:
            return resp,202
        else:
            raise Exception(" Unable to verify restore",resp)
    except Exception:
        raise

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
            raise Exception("Unable to get Service details by API call")
    except Exception:
        raise

