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

from fuel_ccp_tests.managers import ccpmanager


@pytest.fixture(scope='session')
def ccpcluster(config, hardware, underlay, k8scluster):
    """Fixture to get or install fuel-ccp on k8s environment

    :param config: fixture provides oslo.config
    :param hardware: fixture provides enviromnet manager
    :param underlay: fixture provides underlay manager
    :param k8scluster: fixture provides k8scluster model
    :rtype: None

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
    if config.ccp.os_host is None:
        ccpmanager.CCPManager.install_ccp(underlay, config)
        config.ccp.os_host = "TODO: get OpenStack endpoints"
        hardware.create_snapshot('ccp_deployed')
    # TODO(ddmitriev): fixture should return an initialized OpenStack manager
    # that provides endpoints to OpenStack services.


@pytest.fixture(scope='session')
def ccp_actions(ccpcluster):
    """Fixture that provides various actions for CCP using SSH
    """
    return ccpmanager.CCPManager()
