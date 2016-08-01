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

from mcp_tests import logger
from mcp_tests import settings

LOG = logger.logger


@pytest.fixture(scope='class')
def pre_build_deploy_step(env):
    """Install microservices, create config/log files

    :param env: envmanager.EnvironmentManager
    :param master_node: self.env.k8s_ips[0]
    """
    master_node = env.k8s_nodes[0]
    remote = env.node_ssh_client(
        master_node,
        **settings.SSH_NODE_CREDENTIALS)
    topology_path = os.getcwd() + '/mcp_tests/templates/' \
                                  'k8s_templates/k8s_topology.yaml'
    remote.upload(topology_path, './')
    command = [
        '>/var/log/microservices.log',
    ]
    with remote.get_sudo(remote):
        for cmd in command:
            LOG.info(
                "Running command '{cmd}' on node {node_name}".format(
                    cmd=cmd,
                    node_name=master_node.name
                )
            )
            result = remote.check_call(cmd, verbose=True)
            assert result['exit_code'] == 0
        remote.close()
