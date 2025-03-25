import json
from kubernetes import client,config
from kubernetes.stream import stream
import requests
import urllib3
import os
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


current_directory = os.getcwd()
with open(current_directory+"/vars.json")  as f:
    data_json = json.load(f)

# Setting Variables
VIP = data_json["VIP"]
robin_user = data_json["ROBIN_USER"]
robin_passwd = data_json["ROBIN_PASSWD"]
tenant = "Administrators"
port = 29442
ip_pool_name = data_json["ip_pool_name"]
ip_pool_macvlan = data_json["ip_pool_macvlan"]
driver_macvlan = data_json["driver_macvlan"]
driver = data_json["driver"]
netmask = data_json["netmask"]
range = data_json["range"]
range_macvlan = data_json["range_macvlan"]
master_interface = data_json["master_interface"]
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

def ip_pool_allocation(auth_token):
    try:
        responses = []
        file_header = {'Authorization': auth_token, 'Content-type': 'application/json'}
        url = server_url + "/api/v3/robin_server/ip-pools/"
        i = 0
        j = 0
        for ip_pool in ip_pool_name:
            params_obj = {"ip_pool":{
                                        "name":ip_pool,
                                        "ranges":[{"range":range[j]}],
                                        "zoneid":"default",
                                        "driver":driver[i],
                                        "netmask":netmask
                                    }
                         }
            response_obj = requests.post(url, data=json.dumps(params_obj), verify=False, headers=file_header)

            # Get the response code
            response_code = response_obj.status_code
            if response_obj and response_code == 200:
                response = [response_obj.json(), response_obj.status_code]
                responses.append(response)
                i = i + 1
                j = j + 1
            else:
                raise Exception("Unable to allocate ip-pool", response_obj.json(), response_obj.status_code)
        code = 400
        for i in responses:
            if i[1] == 200:
                code = 200
        return [responses,code]
    except Exception:
        raise

def ip_pool_macvlan_allocation(auth_token):
    try:
        file_header = {'Authorization': auth_token, 'Content-type': 'application/json'}
        url = server_url + "/api/v3/robin_server/ip-pools/"
        params_obj = {"ip_pool":{
                                    "name":ip_pool_macvlan,
                                    "ranges":[{"range":range_macvlan}],
                                    "zoneid":"default",
                                    "driver":driver_macvlan,
                                    "netmask":netmask,
                                    "master_interface":master_interface
                                }
                     }
        response_obj = requests.post(url, data=json.dumps(params_obj), verify=False, headers=file_header)

        # Get the response code
        response_code = response_obj.status_code
        if response_obj and response_code == 200:
            response = [response_obj.json(), response_obj.status_code]
            return response
        else:
            raise Exception("Unable to allocate ip-pool", response_obj.json(), response_obj.status_code)
    except Exception:
        raise

