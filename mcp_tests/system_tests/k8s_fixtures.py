#    Copyright 2016 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import pytest

from mcp_tests import settings
from mcp_tests.models.k8s import cluster


@pytest.fixture(scope='function')
def k8sclient(request, env):
    """Fixture to get K8sCluster instance for session

    :param env: envmanager.EnvironmentManager
    :rtype: cluster.K8sCluster
    """
    admin_ip = env.node_ip(env.k8s_nodes[0])
    k8s = cluster.K8sCluster(user=settings.KUBE_ADMIN_USER,
                             password=settings.KUBE_ADMIN_PASS,
                             host=admin_ip,
                             default_namespace='ccp')
    return k8s
