"""
Convenience functions for manipulating stateful sets via kubernetes client.
"""

__author__ = "Michal Cwiertnia"
__copyright__ = "Copyright (C) 2019 ACK CYFRONET AGH"
__license__ = "This software is released under the MIT license cited in " \
              "LICENSE.txt"

import re
from typing import List

from kubernetes.client import V1StatefulSet, V1Pod

from . import pods
from .kubernetes_utils import get_name, get_apps_v1_api_client
from ..one_env_dir.user_config import get_current_namespace


def list_stateful_sets() -> List[V1StatefulSet]:
    client = get_apps_v1_api_client()
    namespace = get_current_namespace()
    return client.list_namespaced_stateful_set(namespace).items


def get_stateful_set_pods(stateful_set: V1StatefulSet) -> List[V1Pod]:
    stateful_set_name = get_name(stateful_set)
    return [pod
            for pod in pods.list_pods()
            if re.match(r'{}-[\d]+'.format(stateful_set_name), get_name(pod))]
