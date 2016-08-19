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

from mcp_tests.managers import ccp
from mcp_tests.logger import logger
from mcp_tests import settings


@pytest.yield_fixture(scope='module')
def admin_node(env, env_with_k8s_and_ccp):
    logger.info("Get SSH access to admin node")
    remote = env.node_ssh_client(
        env.k8s_nodes[0],
        login=settings.SSH_NODE_CREDENTIALS['login'],
        password=settings.SSH_NODE_CREDENTIALS['password'])
    yield remote
    remote.close()


@pytest.fixture(scope='session')
def env_with_k8s_and_ccp(env, env_with_k8s):
    """Fixture to install fuel-ccp on k8s environment

    :param env_with_k8s: envmanager.EnvironmentManager
    """
    params = {
        'config-file': '~/ccp.conf',
        'debug': ''
    }
    manager = ccp.CCPManager(env.k8s_nodes[0], default_params=params)
    manager.install_ccp()

    ccp_globals = {'configs': {
        'private_interface': 'eth0',
        'public_interface': 'eth1',
        'neutron_external_interface': 'eth2'
    }}
    manager.put_yaml_config('/tmp/ccp-globals.yaml', ccp_globals)
    manager.init_default_config()
    return manager


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
    def test_deploy_os_with_custom_keystone(
            self,
            env_with_k8s_and_ccp,
            env_with_k8s,
            admin_node):
        ccp = env_with_k8s_and_ccp
        k8s = env_with_k8s
        k8s.create_registry()
        ccp.fetch()
        admin_node.check_call(
            "rm -fr /home/{}/microservices-repos/fuel-ccp-keystone".format(
                settings.SSH_NODE_CREDENTIALS['login']))
        admin_node.upload(
            source=settings.FUEL_CCP_KEYSTONE_LOCAL_REPO,
            target="/home/{}/microservices-repos/fuel-ccp-keystone".format(
                settings.SSH_NODE_CREDENTIALS['login']))
        ccp.build()
        ccp.deploy()
