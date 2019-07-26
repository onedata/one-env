"""
Convenience functions for manipulating k8s deployments via kubernetes client.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2019 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

from typing import List, Optional

from kubernetes.client import V1Deployment

from .kubernetes_utils import get_name, get_apps_v1_api_client
from ..one_env_dir.user_config import get_current_namespace


def list_k8s_deployments() -> List[V1Deployment]:
    client = get_apps_v1_api_client()
    namespace = get_current_namespace()
    return client.list_namespaced_deployment(namespace).items


def delete_k8s_deployments(namespace: Optional[str] = None) -> None:
    if not namespace:
        namespace = get_current_namespace()
    client = get_apps_v1_api_client()
    deployment_list = list_k8s_deployments()

    for deployment in deployment_list:
        deployment_name = get_name(deployment)
        client.delete_namespaced_deployment(deployment_name, namespace)
