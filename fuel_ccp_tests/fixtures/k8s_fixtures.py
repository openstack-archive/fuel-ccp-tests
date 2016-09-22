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

import os
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
    # If no snapshot was reverted, then try to revert the snapshot
    # that belongs to the fixture.
    # Note: keep fixtures in strict dependences from each other!
    if not revert_snapshot:
        if hardware.has_snapshot(ext.SNAPSHOT.k8s_deployed) and \
                hardware.has_snapshot_config(ext.SNAPSHOT.k8s_deployed):
            hardware.revert_snapshot(ext.SNAPSHOT.k8s_deployed)

    # Create k8s cluster
    if config.k8s.kube_host == '0.0.0.0':
        kube_settings = getattr(request.instance, 'kube_settings',
                                settings.DEFAULT_CUSTOM_YAML)
        LOG.info('Kube settings are {}'.format(kube_settings))

        k8s_actions.install_k8s(
            custom_yaml=kube_settings,
            lvm_config=underlay.config_lvm)
        hardware.create_snapshot(ext.SNAPSHOT.k8s_deployed)

    else:
        # 1. hardware environment created and powered on
        # 2. config.underlay.ssh contains SSH access to provisioned nodes
        #    (can be passed from external config with TESTS_CONFIGS variable)
        # 3. config.k8s.* options contain access credentials to the already
        #    installed k8s API endpoint
        pass

    return k8s_actions


@pytest.fixture(scope='class')
def check_netchecker_files(request):
    files_missing = []
    for arg in request.cls.netchecker_files:
        if not os.path.isfile(arg):
            files_missing.append(arg)
    assert len(files_missing) == 0, \
        ("The following netchecker files not found: "
         "{0}!".format(', '.join(files_missing)))


@pytest.fixture(scope='class')
def check_netchecker_images_settings():
    settings_missing = []
    for setting in ('MCP_NETCHECKER_AGENT_IMAGE_REPO',
                    'MCP_NETCHECKER_AGENT_VERSION',
                    'MCP_NETCHECKER_SERVER_IMAGE_REPO',
                    'MCP_NETCHECKER_SERVER_VERSION'):
        if not getattr(settings, setting, None):
            settings_missing.append(setting)
    assert len(settings_missing) == 0, \
        ("The following environment variables are not set: "
         "{0}!".format(', '.join(settings_missing)))


@pytest.fixture(scope='class')
def check_calico_images_settings():
    assert settings.DEFAULT_CUSTOM_YAML['kube_network_plugin'] == 'calico', \
        "Calico network plugin isn't enabled!"
    if not any(settings.CALICO.values()):
        LOG.warning("No custom settings are provided for Calico! "
                    "Defaults will be used!")
