"""
This module contains basic functions for operations on k8s objects.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import re
from typing import List, Union, Callable, Any, Optional

import urllib3
from kubernetes import config
from kubernetes.client import (CoreV1Api, V1Pod, V1ConfigMap, AppsV1Api,
                               V1StatefulSet, V1Service, V1Deployment)

from .. import terminal


K8sComponent = Union[V1Pod, V1ConfigMap, V1StatefulSet, V1Service,
                     V1Deployment]


def get_core_v1_api_client() -> CoreV1Api:
    urllib3.disable_warnings()
    config.load_kube_config()
    return CoreV1Api()


def get_apps_v1_api_client() -> AppsV1Api:
    urllib3.disable_warnings()
    config.load_kube_config()
    return AppsV1Api()


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


def print_components(components: List[K8sComponent]) -> None:
    for component in components:
        print('    {}'.format(get_name(component)))


def print_choosing_hint() -> None:
    print('')
    terminal.info('To choose a component, provide its full name or any '
                  'matching, unambiguous string. You can use dashes '
                  '("{}") for a wildcard character, e.g.: {} will match {}.'
                  .format(terminal.green_str('-'),
                          terminal.green_str('z-1'),
                          terminal.green_str('dev-onezone-node-1-0')))


def match_components_verbose(substring: str, list_components:
                             Callable[[], List[K8sComponent]],
                             allow_multiple: bool = False) -> Optional[Any]:
    if not substring:
        terminal.error('Please choose a component:')
        print_components(list_components())
        print_choosing_hint()
        return None

    matching_components = match_component(substring, list_components)

    if not matching_components:
        if list_components():
            terminal.error('There are no components matching \'{}\'. '
                           'Choose one of:'.format(substring))
            print_components(list_components())
            print_choosing_hint()
        else:
            terminal.error('There are no components running')
        return None

    if len(matching_components) == 1:
        return matching_components[0]

    if allow_multiple:
        return matching_components

    terminal.error('There is more than one matching component:')
    print_components(matching_components)
    print_choosing_hint()
    return None
