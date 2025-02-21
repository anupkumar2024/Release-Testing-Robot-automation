import json
import paramiko
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
port = 29442
appName = data_json["appName"]
ns = data_json["ns"]
server_url = f"https://{VIP}:{port}"
chart = data_json["chart"]
command = data_json["helm_command"]
nodeip = data_json["nodeip"]
ssh_username = data_json["ssh_username"]
ssh_password = data_json["ssh_password"]
ssh_port = data_json["ssh_port"]


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

def create_helm_stateful_app():
    try:
        # Create an SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # Specify the path of the file you want to copy
        file_to_copy = './nginx-vol-replication-0.1.0.tgz'
        # Specify the path of the destination directory you want to copy to
        destination = '/root/nginx-vol-replication-0.1.0.tgz'
        # Connect to the remote server
        ssh.connect(hostname=nodeip, port=ssh_port, username=ssh_username, password=ssh_password)
        # Use SFTP to transfer the file
        sftp = ssh.open_sftp()
        sftp.put(file_to_copy,destination)
        sftp.close()

        ssh.connect(hostname=nodeip, port=ssh_port, username=ssh_username, password=ssh_password)
        commands = command+" "+appName+" "+chart+" "+"-n"+" "+ns
        # Execute the Helm command
        stdin, stdout, stderr = ssh.exec_command(commands)
        return stdout.read().decode()
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

def fetch_pvc():
    try:
        time.sleep(5)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=nodeip, port=ssh_port, username=ssh_username, password=ssh_password)
        stdin, stdout, stderr = ssh.exec_command("kubectl get pvc -n " + ns + " | grep -v NAME | awk \'{print $3}\'")
        pvc = stdout.read().decode().strip()
        return pvc
        ssh.close()
    except Exception:
        raise

def verify_vol_replication(auth_token):
    try:
        time.sleep(5)
        pvc_name = fetch_pvc()
        file_header = {'Authorization': auth_token, 'Content-type': 'application/json'}
        url = server_url + "/api/v3/robin_server/volumes"
        params_obj = {"name": pvc_name}
        response_obj = requests.get(url, data=json.dumps(params_obj), verify=False, headers=file_header)
        # Get the response code
        response_code = response_obj.status_code
        if response_obj and response_code == 200:
            data = response_obj.json()
            item = data["items"]["alloc"]
            length = len(item)
            if length == 2 and item[0][0]["wwn"] != item[1][0]["wwn"]:
                return 200,item,length
            else:
                raise Exception("volume replication failed",length,item)
    except Exception:
        raise
