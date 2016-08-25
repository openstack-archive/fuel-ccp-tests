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

from fuel_ccp_tests import logger
from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests import settings
from fuel_ccp_tests.managers import k8smanager

LOG = logger.logger


@pytest.fixture(scope='function')
def k8s_actions(config, underlay):
    """Fixture that provides various actions for K8S

    :param config: fixture provides oslo.config
    :param underlay: fixture provides underlay manager
    :rtype: K8SManager

    For use in tests or fixtures to deploy a custom K8S
    """
    return k8smanager.K8SManager(config, underlay)


@pytest.fixture(scope='function')
def k8scluster(revert_snapshot, request, config,
               hardware, underlay, k8s_actions):
    """Fixture to get or install k8s on environment

    :param request: fixture provides pytest data
    :param config: fixture provides oslo.config
    :param hardware: fixture provides enviromnet manager
    :param underlay: fixture provides underlay manager
    :param k8s_actions: fixture provides K8SManager instance
    :rtype: K8SManager

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
    # Try to guess environment config for reverted snapshot
    if revert_snapshot and config.k8s.kube_host == '0.0.0.0':
        config.k8s.kube_host = underlay.host_by_node_name(
            underlay.node_names()[0])

    # Create k8s cluster
    if config.k8s.kube_host == '0.0.0.0':
        kube_settings = getattr(request.instance, 'kube_settings',
                                settings.DEFAULT_CUSTOM_YAML)
        LOG.info('Kube settings are {}'.format(kube_settings))
        k8s_actions.install_k8s(custom_yaml=kube_settings)

        hardware.create_snapshot(ext.SNAPSHOT.k8s_deployed)

    else:
        # 1. hardware environment created and powered on
        # 2. config.underlay.ssh contains SSH access to provisioned nodes
        #    (can be passed from external config with TESTS_CONFIGS variable)
        # 3. config.k8s.* options contain access credentials to the already
        #    installed k8s API endpoint
        pass

    return k8s_actions
