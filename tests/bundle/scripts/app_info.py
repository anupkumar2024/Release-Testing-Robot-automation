import sys
import json

def get_app_info(app_config):
    app_info = {}
    service_url = None

    host = app_config['roles'][0]['vnodes'][0]['hostname']
    service_url = "http://%s:80" % host

    if service_url:
        app_info['service_urls'] = [{"name": "Nginx", "url": service_url}]

    return json.dumps(app_info)

if __name__ == '__main__':
    json_file = sys.argv[1]
    with open(json_file) as f:
        app_config = json.load(f)

    print(get_app_info(app_config))

