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

from mcp_tests.models.k8smanager import K8SManager


@pytest.fixture(scope='session')
def k8scluster(config, hardware, underlay):
    """Fixture to install k8s on environment

    :param env: envmanager.EnvironmentManager
    """
    """Fixture to get K8sCluster instance for session

    :param env: envmanager.EnvironmentManager
    :rtype: cluster.K8sCluster
    """

    if config.k8s.kube_host is None:
        kube_settings = getattr(request.instance, 'kube_settings',
                                settings.DEFAULT_CUSTOM_YAML)
        admin_ip = K8SManager.install_k8s(underlay, custom_yaml=kube_settings)
        config.k8s.kube_host = admin_ip
        hardware.create_snapshot('k8s_deployed')

    k8scluster = cluster.K8sCluster(user=config.k8s.kube_admin_user,
                                    password=config.k8s.kube_admin_pass,
                                    host=config.k8s.kube_host)
    return k8scluster


@pytest.fixture(scope='session')
def k8s_actions(k8scluster):
    """Fixture that provides various actions for K8S using SSH
    """
    return K8SManager()
