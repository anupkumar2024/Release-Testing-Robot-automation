import json
import os
import paramiko
from kubernetes import client,config
from kubernetes.stream import stream
import requests
import urllib3
import time
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


current_directory = os.getcwd()
with open(current_directory+"/vars.json")  as f:
    data_json = json.load(f)

#Initialize variables
VIP = data_json["VIP"]
robin_user = data_json["ROBIN_USER"]
robin_passwd = data_json["ROBIN_PASSWD"]
port = 29442
appName = data_json["appName"]
snapName = data_json["snapName"]
ns = data_json["ns"]
repo = data_json["repo"]
server_url = f"https://{VIP}:{port}"
chart = data_json["chart"]
command = data_json["helm_command"]
nodeip = data_json["nodeip"]
ssh_username = data_json["ssh_username"]
ssh_password = data_json["ssh_password"]
ssh_port = data_json["ssh_port"]
remote_file_path_helm_pod = data_json["remote_file_path_helm_pod"]

def robin_login():
    try:
        ip_url = f"https://{VIP}:"
        login_url = ip_url + str(port) + "/api/v3/robin_server/login"
        robin_obj = requests.post(login_url, json={'password': robin_passwd, 'username': robin_user, 'tenant': "Administrators"},
                                  verify=False,
                                  headers={'Content-type': 'application/json'})
        res_obj = robin_obj.json()
        auth_token = res_obj["token"]
        list = [res_obj,auth_token,robin_obj.status_code]
        return list
    except Exception as error:
        return error,robin_obj.status_code

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
    except Exception as error:
        return error,response
    
    
def create_helm_app():
    try:
        # Create an SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh.connect(hostname=nodeip, port=ssh_port, username=ssh_username, password=ssh_password)
        commands = command+" "+appName+" "+chart+" "+"-n"+" "+ns
        # Execute the Helm command
        stdin, stdout, stderr = ssh.exec_command(commands)
        return stdout.read().decode(),stderr.read().decode()
        ssh.close()
        ssh.connect(hostname=nodeip, port=ssh_port, username=ssh_username, password=ssh_password)
        while True:
            stdin, stdout, stderr = ssh.exec_command("kubectl get sts -n "+ns+" | grep -v NAME | awk \'{print $2}\'")
            output = stdout.read().decode().strip()
            if output == "1/1":
                break
        ssh.close()
    except Exception as error:
        return error


def register_helm_app(auth_token):
    try:
        # Create an SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=nodeip, port=ssh_port, username=ssh_username, password=ssh_password)
        commands = "/usr/bin/kubectl get all -n "+ns+" | awk \'{print $1}\'| grep -v NAME"
        stdin, stdout, stderr = ssh.exec_command(commands)
        resources_list = stdout.read().decode().split()
        ssh.close()

        file_header = {'Authorization': auth_token, 'Content-type': 'application/json'}
        url = server_url + "/api/v3/robin_server/k8s_app"
        params_obj = {
            "action": "register",
            "query": {
                "apps": ["helm/"+appName],
                "selectors": [],
                "resources": resources_list,
                "namespace": ns,
            },
            "name": appName,
            "namespace": ns,
            "app_type": "helm",
        }
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
            response = [response_obj.json(), response_obj.status_code]
            return response
        else:
            raise Exception(response_obj.json(),response_obj.status_code)

    except Exception:
        raise

# Get pod name
def get_pod_name(kubeconfig_path):
    try:
        time.sleep(5)
        while True:
            config.load_kube_config(kubeconfig_path)
            # Create Kubernetes API client
            api_instance = client.CoreV1Api()
            api_response = api_instance.list_namespaced_pod(namespace=ns,label_selector="app=nginx")
            for pod in api_response.items:
                pod_name = pod.metadata.name
                pod_status = pod.status.phase
                container_status = pod.status.container_statuses[0]
                container_name = container_status.name
                container_ready = container_status.ready
                if pod_status == "Running" and container_ready == True:
                    break
            return [pod_name,container_name,container_ready,pod_status]
    except Exception:
        raise

#upload file to pod
def upload_file_to_pod(kubeconfig_path):
    try:
        pod_details = get_pod_name(kubeconfig_path)
        local_file_path = 'demofile.txt'

        with open(local_file_path, "w") as f:
            f.write("Now the file has more content!")

        # Load kubeconfig
        config.load_kube_config(kubeconfig_path)

        # Read the file content
        with open(local_file_path, 'rb') as file:
            file_content = file.read()
        # Define the command to create the file in the pod
        exec_command = [
            'sh',
            '-c',
            f'cat > {remote_file_path_helm_pod}'
        ]
        exec_command_get = [
            'sh',
            '-c',
            f'cat  {remote_file_path_helm_pod}'
        ]

        # Create an API client
        api_instance = client.CoreV1Api()
        # Execute the command in the pod
        resp = stream(api_instance.connect_get_namespaced_pod_exec,
                      name=pod_details[0],
                      namespace=ns,
                      container=pod_details[1],
                      command=exec_command,
                      stderr=True, stdin=True,
                      stdout=True, tty=False, _preload_content=False)
        # Send the file content to the pod
        resp.write_stdin(file_content)
        resp.close()
        api_instance = client.CoreV1Api()
        resp = stream(api_instance.connect_get_namespaced_pod_exec,
                      name=pod_details[0],
                      namespace=ns,
                      command=exec_command_get,
                      stderr=True, stdin=True,
                      stdout=True, tty=False)
        if resp == file_content.decode():
            return 200
        else:
            raise Exception("File not uploaded",resp)
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

def delete_data_from_pod(kubeconfig_path):
    try:
        pod_details = get_pod_name(kubeconfig_path)
        config.load_kube_config(kubeconfig_path)

        # Define the command to delete the file in the pod
        exec_command = [
            'sh',
            '-c',
            f'rm -rf  {remote_file_path_helm_pod}'
        ]
        api_instance = client.CoreV1Api()
        # Execute the command in the pod
        stream(api_instance.connect_get_namespaced_pod_exec,
                      name=pod_details[0],
                      namespace=ns,
                      container=pod_details[1],
                      command=exec_command,
                      stderr=True, stdin=True,
                      stdout=True, tty=False)

    except Exception:
        raise

def fetch_snapshot_id(auth_token):
    try:
        file_header = {'Authorization': auth_token, 'Content-type': 'application/json'}
        url = server_url + "/api/v6/robin_server/appsview?akind=helm&parentapp="+appName+"&atype=SNAPSHOT&namespace="+ns
        response_obj = requests.get(url, verify=False, headers=file_header)
        if response_obj and response_obj.status_code == 200:
            data = response_obj.json()
            for item in data["k8s"]:
                return item["id"],response_obj.status_code
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

def verify_data_restore(kubeconfig_path):
    try:
        pod_details = get_pod_name(kubeconfig_path)

        with open("demofile.txt", 'r') as file:
            file_content = file.read()

        config.load_kube_config(kubeconfig_path)
        # Define the command to delete the file in the pod
        exec_command = [
            'sh',
            '-c',
            f'cat  {remote_file_path_helm_pod}'
        ]
        api_instance = client.CoreV1Api()
        # Execute the command in the pod
        resp = stream(api_instance.connect_get_namespaced_pod_exec,
                      name=pod_details[0],
                      namespace=ns,
                      container=pod_details[1],
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
        url = server_url + "/api/v6/robin_server/apps/"+appName+"?force=True"
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
            raise Exception("Unable to get Service details by API call",response_code,response_obj.json())
    except Exception:
        raise

