import json
import paramiko
from kubernetes import client,config
from kubernetes.stream import stream
import requests
import urllib3
import time
import os
from backup_restore_bundle import register_external_repo
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# def get_data(vars_json):
#     """
#     This function receives JSON data (as a string or file-like object) from Robot Framework,
#     parses it, and initializes variables dynamically.
#     """
#     # Parse the JSON data
#     global data_json
#     data_json = None
#     if isinstance(vars_json, str):
#         data_json = json.loads(vars_json)  # Parse JSON string
#     else:
#         data_json = json.load(vars_json)  # Parse JSON from file-like object

current_directory = os.getcwd()
with open(current_directory+"/vars.json")  as f:
    data_json = json.load(f)

    
# Initialize variables
VIP = data_json["VIP"]
robin_user = data_json["ROBIN_USER"]
robin_passwd = data_json["ROBIN_PASSWD"]
tenant = "Administrators"  # Static value
port = 29442  # Static value
appName = data_json["appName"]
ns = data_json["ns"]
repo = data_json["repo"]
remote_file_path = data_json["remote_file_path"]
minio = data_json["minio"]
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
        robin_obj = requests.post(login_url, json={'password': robin_passwd, 'username': robin_user, 'tenant': tenant},
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


# method to register help app with robin
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

def register_ext_storage_repo(auth_token):
    response = register_external_repo(auth_token)
    return(response)


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

# method to attach app to external repo
def attach_app_to_ext_repo(auth_token):
    time.sleep(5)
    file_header = {'Authorization': auth_token, 'Content-type': 'application/json'}
    url = server_url + "/api/v3/robin_server/apps/" + appName
    params_obj = {"action":"add_repo","name":appName,"repo_name":repo,"namespace": ns}
    response_obj = requests.put(url, data=json.dumps(params_obj), verify=False, headers=file_header)
    if response_obj and response_obj.status_code == 202:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=nodeip, port=ssh_port, username=ssh_username, password=ssh_password)
        data = response_obj.json()
        jobid = str(data["jobid"])
        get_url = server_url + "/api/v5/robin_server/jobs/" + jobid
        while True:
            stdin, stdout, stderr = ssh.exec_command("kubectl get sts -n "+ns+" | grep -v NAME | awk \'{print $2}\'")
            output = stdout.read().decode().strip()
            get_resp = requests.get(get_url, verify=False, headers=file_header)
            job_details = get_resp.json()["job"][0]
            if output == "1/1" and job_details["state"] == 10 and job_details['error'] == 0 and get_resp.status_code == 200:
                break
        response = [response_obj.json(),response_obj.status_code]
        return response
    else:
        raise Exception(response_obj.status_code)

# Method to create backup of helm app
def backup_creation(auth_token):
    try:
        file_header = {'Authorization': auth_token, 'Content-type': 'application/json'}
        url = server_url + "/api/v3/robin_server/apps"
        # snapshotid = get_snapshot_id(server_url,auth_token)
        params_obj = {"action":"backup","app_name":appName,"repo":repo,"backup_name":"nginx-backup"}
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
            raise Exception("backup creation failed",response_code,response_obj.json())
    except Exception:
        raise

# method to detach app from repo
def detach_app_from_repo(auth_token):
    try:
        file_header = {'Authorization': auth_token}
        url = server_url + "/api/v3/robin_server/apps/"+appName
        params_obj = {"action": "remove_repo", "name": appName, "repo_name": repo,"namespace":ns}
        response_obj = requests.put(url,data=json.dumps(params_obj),verify=False, headers=file_header)

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
            response = [response_obj.json(), response_obj.status_code]
            raise Exception("Unable to detach app from repo",response)
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
        time.sleep(5)
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
            # delete pvc
            # ssh = paramiko.SSHClient()
            # ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            # ssh.connect(hostname=nodeip, port=ssh_port, username=ssh_username, password=ssh_password)
            # stdin,stdout,stderr = ssh.exec_command("kubectl get pvc -n "+ns+" | grep -v NAME | awk \'{print $1}\'| xargs kubectl delete pvc -n "+ns)
            # output = stdout.read().decode()
            # response.append(output)
            return response
        else:
            response = [response_obj.json(), response_obj.status_code]
            raise Exception(response)
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
                if item["state"] == "Pushed" and item["name"] == "nginx-backup" and item["app"] == appName:
                    backupid = item["id"]
                    backupid_list.append(backupid)
            return [str(backupid), response_obj.status_code,backupid_list]
        else:
            raise Exception(response_code,response_obj.json())
    except Exception:
        raise

# method to restore  helm app from backup
def app_restore_from_backup(auth_token):
    try:
        file_header = {'Authorization': auth_token}
        backupid = fetch_backup_id(auth_token)
        if backupid[0] == 0:
            raise Exception("Backup Id is invalid")
        get_url = server_url + "/api/v3/robin_server/storage_repo?sub-command=get-backup-info&backupid="+backupid[0]+""
        resp = requests.get(get_url, verify=False, headers=file_header)
        configs = { "action":"create",
                    "name":appName,
                    "namespace":ns,
                    "source_type":"backup",
                    "source_id":backupid[0],
                    "hydrate":False,
                    "same_name_namespace":True,
                    "repo_name":repo
                  }
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
            raise Exception(response_code, response_obj)
    except Exception:
        raise

# unregister helm app from robin
def unregister_helm_app(auth_token):
    try:
        file_header = {'Authorization': auth_token, 'Content-type': 'application/json'}
        url = server_url + "/api/v3/robin_server/k8s_app"
        params_obj = { "action": "unregister","name": appName,"namespace": ns }
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
            raise Exception(response_obj.json(), response_obj.status_code)

    except Exception:
        raise

# method to hydrate volumes
def hydrate_volumes(auth_token):
    try:
        # get pv from pvc
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=nodeip, port=ssh_port, username=ssh_username, password=ssh_password)
        stdin, stdout, stderr = ssh.exec_command("kubectl get pvc -n " + ns + " | grep -v NAME | awk \'{print $3}\'")
        output = stdout.read().decode().split()
        file_header = {'Authorization': auth_token, 'Content-type': 'application/json'}
        url = server_url + "/api/v3/robin_server/volumes"
        for vol in output:
            params_obj = {"action": "hydrate", "name": vol,}
            response_obj = requests.put(url, data=json.dumps(params_obj), verify=False, headers=file_header)
        if response_obj and response_obj.status_code == 202:
            response = [response_obj.json(), response_obj.status_code]
            return response
        else:
            raise(response_obj.json(), response_obj.status_code)
    except Exception:
        raise

# method to list file from pod
def list_file_from_pod(kubeconfig_path):
    try:
        time.sleep(5)
        pod_details = get_pod_name(kubeconfig_path)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=nodeip, port=ssh_port, username=ssh_username, password=ssh_password)
        while True:
            stdin, stdout, stderr = ssh.exec_command("kubectl get sts -n "+ns+" | grep -v NAME | awk \'{print $2}\'")
            output = stdout.read().decode().strip()
            if output == "1/1":
                break
        ssh.close()
        # Load kubeconfig
        config.load_kube_config(kubeconfig_path)

        # Define the command to create the file in the pod
        exec_command = ['cat', remote_file_path_helm_pod]

        # Create an API client
        api_instance = client.CoreV1Api()

        # Execute the command in the pod
        resp = stream(api_instance.connect_get_namespaced_pod_exec,
                      name=pod_details[0],
                      namespace=ns,
                      command=exec_command,
                      stderr=True, stdin=True,
                      stdout=True, tty=False)

        with open("demofile.txt", 'r') as file:
            file_content = file.read()

        if file_content == resp:
            return 202
        else:
            raise Exception("Data not restored",resp)
    except Exception:
        raise

def verify_helm_pod(kubeconfig_path):
    try:
        pod_details = get_pod_name(kubeconfig_path)
        if pod_details[0] == "nginx-server-0" and pod_details[1] == "nginx":
            return [pod_details,200]
        else:
            raise Exception("pods are not intact after deregistration")
    except Exception:
        raise


def helm_app_cleanup():
    try:
        # Delete helm app
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=nodeip, port=ssh_port, username=ssh_username, password=ssh_password)
        commands = "/root/bin/helm delete" + " " + appName + " " + "-n" + " " + ns
        stdin, stdout, stderr = ssh.exec_command(commands)
        ssh.close()
        response = [stdout.read().decode()]
        return response
    except Exception:
        raise
    

def repo_cleanup(auth_token):    
    try:
        time.sleep(10)    
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


def delete_backups(auth_token):
    try:
        response = []
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
                response.append(response_obj.status_code)
            else:
                raise Exception("Unable to delete backup", response_obj.json(), response_obj.status_code)
        codes = []
        for i in response:
            if i == 202:
                codes.append(True)
            else:
                codes.append(False)
        if all(codes):
            return 202
        else:
            return 500
    except Exception:
        raise
