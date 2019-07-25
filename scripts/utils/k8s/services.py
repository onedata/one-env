"""
Convenience functions for manipulating k8s services via kubernetes client.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2019 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

from typing import List

from kubernetes.client import V1Service

from .kubernetes_utils import get_core_v1_api_client, get_name
from ..one_env_dir.user_config import get_current_namespace


def list_k8s_services() -> List[V1Service]:
    client = get_core_v1_api_client()
    namespace = get_current_namespace()
    return client.list_namespaced_service(namespace).items


def delete_k8s_services(namespace: str = get_current_namespace()) -> None:
    client = get_core_v1_api_client()
    services_list = list_k8s_services()

    for service in services_list:
        service_name = get_name(service)
        client.delete_namespaced_service(service_name, namespace)
