"""
This module contains basic functions for operations on k8s objects.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import re
from typing import List, Union, Callable

import urllib3
from kubernetes import config
from kubernetes.client import CoreV1Api, V1Pod, V1ConfigMap


K8sComponent = Union[V1Pod, V1ConfigMap]


def get_kube_client() -> CoreV1Api:
    urllib3.disable_warnings()
    config.load_kube_config()
    kube = CoreV1Api()
    return kube


def get_name(component: K8sComponent) -> str:
    return component.metadata.name


def get_chart_name(component: K8sComponent) -> str:
    return component.metadata.labels.get('chart')


def match_component(substring: str, list_components:
                    Callable[[], List[K8sComponent]]) -> List[K8sComponent]:
    components = list_components()

    pattern = '.*{}.*'.format(substring.replace('-', '.*'))
    return list(filter(lambda comp: re.match(pattern, get_name(comp)),
                       components))
