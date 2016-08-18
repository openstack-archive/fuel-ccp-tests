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
from mcp_tests.managers import k8smanager


@pytest.fixture(scope='session')
def k8scluster(request, config, hardware, underlay):
    """Fixture to get or install k8s on environment

    :param request: fixture provides pytest data
    :param config: fixture provides oslo.config
    :param hardware: fixture provides enviromnet manager
    :param underlay: fixture provides underlay manager
    :rtype: K8sCluster

    If config.k8s.kube_host is not set, this fixture assumes that
    the k8s cluster was not deployed, and do the following:
    - deploy k8s cluster
    - make snapshot with name 'k8s_deployed'
    - return K8sCluster instance

    If config.k8s.kube_host was set, this fixture assumes that the k8s
    cluster was already deployed, and do the following:
    - return K8sCluster instance

    If you want to revert 'k8s_deployed' snapshot, please use mark:
    @pytest.mark.revert_snapshot("k8s_deployed")
    """

    if config.k8s.kube_host is None:
        kube_settings = getattr(request.instance, 'kube_settings',
                                settings.DEFAULT_CUSTOM_YAML)
        admin_ip = k8smanager.K8SManager.install_k8s(underlay, custom_yaml=kube_settings)
        config.k8s.kube_host = admin_ip
        hardware.create_snapshot('k8s_deployed')

    k8sclient = k8smanager.K8SManager.get_k8sclient(config)
    return k8sclient


@pytest.fixture(scope='session')
def k8s_actions(k8scluster):
    """Fixture that provides various actions for K8S
    """
    return K8SManager()
