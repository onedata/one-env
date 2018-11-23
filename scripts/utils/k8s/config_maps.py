"""
Convenience functions for manipulating config maps via kubectl.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2018 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

from typing import List, Optional, Dict

import yaml
from kubernetes.client import V1ConfigMap

from ..one_env_dir import user_config
from ..k8s.kubernetes_utils import get_kube_client, match_component


def list_config_maps() -> List[V1ConfigMap]:
    kube_client = get_kube_client()
    namespace = user_config.get_current_namespace()
    config_maps = kube_client.list_namespaced_config_map(namespace)
    return config_maps.items


def match_config_map(substring: str) -> V1ConfigMap:
    config_map = match_component(substring, list_config_maps)
    return config_map[0]


def get_service_type(config_map: V1ConfigMap) -> Optional[str]:
    return config_map.metadata.labels.get('component')


def get_service_config(config_map: V1ConfigMap) -> Optional[Dict[str, Dict]]:
    service_type = get_service_type(config_map)
    config_field = '{}_CONFIG'.format(service_type).upper()
    config = config_map.data.get(config_field)
    if config:
        return yaml.load(config)
    return None


def get_service_name(config_map: V1ConfigMap) -> Optional[str]:
    service_type = get_service_type(config_map)
    config = get_service_config(config_map)
    if config:
        return config.get(service_type).get('name')
    return None


def get_domain(config_map: V1ConfigMap) -> Optional[str]:
    service_type = get_service_type(config_map)
    config = get_service_config(config_map)
    domain_field = 'domainName' if service_type == 'onezone' else 'domain'
    return config.get(service_type).get(domain_field)
