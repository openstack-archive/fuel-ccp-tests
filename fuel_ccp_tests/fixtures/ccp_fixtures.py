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

from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests import settings_oslo
from fuel_ccp_tests.managers import ccpmanager


@pytest.fixture(scope='function')
def ccp_actions(config, underlay):
    """Fixture that provides various actions for CCP

    :param config: fixture provides oslo.config
    :param underlay: fixture provides underlay manager
    :rtype: CCPManager

    For use in tests or fixtures to deploy a custom CCP
    """
    return ccpmanager.CCPManager(config, underlay)


@pytest.fixture(scope='function')
def ccpcluster(revert_snapshot_name, config, hardware,
               underlay, k8scluster, ccp_actions):
    """Fixture to get or install fuel-ccp on k8s environment

    :param config: fixture provides oslo.config
    :param hardware: fixture provides enviromnet manager
    :param underlay: fixture provides underlay manager
    :param k8scluster: fixture provides an installed k8s cluster
    :param ccp_actions: fixture provides CCPManager instance
    :rtype: CCPManager

    If config.ccp.os_host is not set, this fixture assumes that
    the ccp cluster was not deployed, and do the following:
    - deploy ccp cluster
    - make snapshot with name 'ccp_deployed'
    - (TODO)return CCPCluster instance, None at the moment

    If config.ccp.os_host was set, this fixture assumes that the ccp
    cluster was already deployed, and do the following:
    - (TODO)return CCPCluster instance, None at the moment

    If you want to revert 'ccp_deployed' snapshot, please use mark:
    @pytest.mark.revert_snapshot("ccp_deployed")
    """
    if revert_snapshot_name:
        # Load 'config' object from 'config_<revert_snapshot_name>.ini' file
        settings_oslo.reload_snapshot_config(config, revert_snapshot_name)

        if revert_snapshot_name == ext.SNAPSHOT.ccp_deployed \
                and hardware.has_snapshot(ext.SNAPSHOT.ccp_deployed):
            hardware.revert_snapshot(ext.SNAPSHOT.ccp_deployed)

    if config.ccp.os_host is None:
        ccp_actions.install_ccp()
        config.ccp.os_host = "TODO: get OpenStack endpoints"
        # Save 'config' object to 'config_ccp_deployed.ini' file
        settings_oslo.save_config(config, ext.SNAPSHOT.ccp_deployed)

        if not hardware.has_snapshot(ext.SNAPSHOT.ccp_deployed):
            hardware.create_snapshot(ext.SNAPSHOT.ccp_deployed)
        else:
            # TODO(ddmitriev): consider if the previous snapshot should be
            # removed or not?
            pass
    else:
        # 1. hardware environment created and powered on
        # 2. config.underlay.ssh contains SSH access to provisioned nodes
        #    (can be passed from external config with TESTS_CONFIGS variable)
        # 3. config.k8s.* options contain access credentials to the already
        #    installed k8s API endpoint
        # 4. config.ccp.os_host contains an IP address of CCP admin node
        #    (not used yet)
        pass

    return ccp_actions
