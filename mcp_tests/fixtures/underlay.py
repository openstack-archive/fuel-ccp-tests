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
from devops import error
import pytest

from mcp_tests.helpers import ext
from mcp_tests import logger
from mcp_tests import settings
from mcp_tests.managers import envmanager
from mcp_tests.models import underlay_ssh_manager


LOG = logger.logger
UNDERLAY_SNAPSHOT_SUFFIX = "underlay"


def make_snapshot_name(env, suffix, default):
    """Creating snapshot name

    :param request: pytest.python.FixtureRequest
    :param suffix: string
    :param default: string or None
    :rtype: string or None
    """
    if env:
        if suffix:
            return "{0}_{1}".format(
                env.d_env_name,
                suffix
            )
        else:
            return "{0}_{1}".format(
                env.d_env_name,
                default
            )
    return default


@pytest.fixture(scope="session")
def hardware(config):
    """Fixture for manage the hardware layer.

       - start/stop/reboot libvirt/IPMI(/MaaS?) nodes
       - snapshot/revert libvirt nodes (fuel-devops only)
       - block/unblock libvirt  networks/interfaces (fuel-devops only)

       This fixture should get a hardware configuration from
       'config' object or create a virtual/baremetal underlay
       using EnvironmentManager.

       Input data:
           config.hardware.manager: one of ('devops', 'maas', None)
           config.hardware.config: path to the config file for the manager
           ...
           (additional variables for the hardware manager)

       Output data:
        - config.status_name = Latest created or reverted snapshot name
        - config.underlay.ssh = JSONList of SSH access credentials for nodes:
          [
            {
              node_name: node1,
              address_pool: 'public-pool01',
              host: ,
              port: ,
              keys: [],
              get_keys_from: None,
              login: ,
              password: ,
            },
            {
              node_name: node1,
              address_pool: 'private-pool01',
              host:
              port:
              keys: []
              get_keys_from: None,
              login:
              password:
            },
            {
              node_name: node2,
              address_pool: 'public-pool01',
              get_keys_from: node1
              ...
            }
            ,
            ...
          ]
    """
    config_ssh = []  # No defaults, should be read from config
    snapshot_name = UNDERLAY_SNAPSHOT_SUFFIX
    env = None

    manager = config.hardware.manager

    if manager is None:
        # No environment manager is used.
        # 'config' should contain config.underlay.ssh settings
        # 'config' should contain config.underlay.snapshot setting
        pass

    if manager == 'devops':

        config_ssh = []
        snapshot_name = UNDERLAY_SNAPSHOT_SUFFIX
        env = envmanager.EnvironmentManager(
            config_file=config.hardware.conf_path)

        try:
            env.get_env_by_name(env.d_env_name)
        except error.DevopsObjNotFound:
            LOG.info("Environment doesn't exist, creating a new one")
            env.create_environment()
            env.create_snapshot(make_snapshot_name(env,
                                                   snapshot_name,
                                                   None))
            LOG.info("Environment created")

        if config.underlay.ssh == []:
            # Fill config.underlay.ssh from fuel-devops
            for d_node in env.k8s_nodes:
                ssh_data = {
                    'node_name': d_node.name,
                    'address_pool': env.get_network_pool(
                        ext.NETWORK_TYPE.public).address_pool.name,
                    'host': env.node_ip(d_node),
                    'login': settings.SSH_NODE_CREDENTIALS['login'],
                    'password': settings.SSH_NODE_CREDENTIALS['password'],
                }
                config_ssh.append(ssh_data)

            config.underlay.ssh = config_ssh

    return env


@pytest.fixture(scope="session")
def underlay(config, hardware):
    """Fixture that should provide SSH access to underlay objects.

       Input data:
        - config.underlay.ssh : JSONList, *must* be provided, from 'hardware'
                                fixture or from an external config

    :rtype: Object that can select and return nodes.
    """
    return underlay_ssh_manager.UnderlaySSHManager(config.underlay.ssh)
