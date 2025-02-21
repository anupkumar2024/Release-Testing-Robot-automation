from kubernetes import client, config, utils
import json
import yaml
import os

current_directory = os.getcwd()
with open(current_directory+"/vars.json")  as f:
    data_json = json.load(f)

# Setting variables
ns = data_json["ns"]

def load_yaml_with_namespace():
    with open(current_directory+"/tests/pod_hard_antiaffinity.yaml") as f:
        docs = list(yaml.safe_load_all(f))
        for doc in docs:
            if 'metadata' in doc:
                doc['metadata']['namespace'] = ns
    return docs

def create_app(kubeconfig_path):
    try:
        config.load_kube_config(kubeconfig_path)
        # Create an instance of the API class
        k8s_client = client.ApiClient()
        # Apply the YAML file
        docs = load_yaml_with_namespace()
        for doc in docs:
            resp = utils.create_from_dict(k8s_client, doc)
        return resp
    except Exception as e:
        print(e)

def get_pod_node_name(kubeconfig_path):
    try:
        config.load_kube_config(kubeconfig_path)
        v1 = client.CoreV1Api()
        nodes = []
        # Get the pod details
        api_response = v1.list_namespaced_pod(namespace=ns,label_selector="app=nginx-hard")
        for pod in api_response.items:
            node_name = pod.spec.node_name
            nodes.append(node_name)
        return nodes
    except Exception as e:
        print(e)

def verify_pod_hard_anti_affinity(kubeconfig_path):
    nodes = get_pod_node_name(kubeconfig_path)
    if len(nodes) == len(set(nodes)):
        return 200,nodes
    else:
        return 400,"pod hard anti affinity test failed"
    

def app_cleanup(kubeconfig_path):
    try:
        with open(current_directory+"/tests/pod_hard_antiaffinity.yaml") as f:
            docs = list(yaml.safe_load_all(f))
            for doc in docs:
                if doc.get('kind') == 'Deployment' and 'metadata' in doc:
                    deployment_name = doc['metadata'].get('name')

        config.load_kube_config(kubeconfig_path)
        # Create an instance of the API class
        apps_v1 = client.AppsV1Api()
        resp = apps_v1.delete_namespaced_deployment(name=deployment_name, namespace=ns)
        return resp
    except Exception:
        raise

