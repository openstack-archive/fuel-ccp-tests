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

from fuel_ccp_tests.logger import logger
from fuel_ccp_tests import settings


@pytest.fixture(scope='module')
def preconfig(config, underlay):
    logger.info("Preconfiguration for use ccp_deployed snapshot")
    k8s_nodes = underlay.node_names()
    k8s_admin_ip = underlay.host_by_node_name(k8s_nodes[0])
    config.k8s.kube_host = k8s_admin_ip
    return config


@pytest.fixture(scope='module')
def ccp(preconfig, ccp_actions, k8scluster):
    """Fixture to install fuel-ccp on k8s environment

    :param env_with_k8s: envmanager.EnvironmentManager
    """
    ccp_actions.install_ccp()
    ccp_globals = settings.CCP_DEFAULT_GLOBALS
    ccp_actions.put_yaml_config(settings.CCP_CLI_PARAMS['deploy-config'],
                                ccp_globals)
    ccp_actions.default_params = settings.CCP_CLI_PARAMS
    ccp_actions.init_default_config()
    return ccp_actions


class TestPreCommitKeystone(object):
    """docstring for TestPreCommitKeystone

    Scenario:
        1. Install k8s
        2. Install fuel-ccp
        3. Fetch all repositories
        4. Fetch keystone from review
        5. Fetch containers from external registry
        6. Build keytone container
        7. Deploy Openstack
        8. Run tempest
    """

    @pytest.mark.keystone
    @pytest.mark.revert_snapshot(name='k8s_deployed')
    def test_deploy_os_with_custom_keystone(
            self, ccp, k8s_actions, underlay, rally):

        k8s_actions.create_registry()
        ccp.fetch()
        ccp.update_service('keystone',
                           settings.FUEL_CCP_KEYSTONE_LOCAL_REPO)
        ccp.build('base-tools', suppress_output=False)
        ccp.build(suppress_output=False)
        ccp.deploy()
        rally.prepare()
        rally.pull_image()
        rally.run()
        rally.run_tempest('identity')
