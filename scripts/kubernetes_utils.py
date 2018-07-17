import re
import urllib3
from kubernetes import client, config


def get_kube_client():
    urllib3.disable_warnings()
    config.load_kube_config()
    kube = client.CoreV1Api()
    return kube


def get_name(component):
    return component.metadata.name


def get_chart_name(component):
    return component.metadata.labels.get('chart')


def match_component(substring: str, list_components):
    components_list = list_components()

    pattern = '.*{}.*'.format(substring.replace('-', '.*'))
    return list(filter(lambda comp: re.match(pattern, get_name(comp)),
                       components_list))
