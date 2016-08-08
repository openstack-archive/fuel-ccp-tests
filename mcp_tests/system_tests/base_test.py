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
import copy
import subprocess
import os

import pytest
import yaml

from mcp_tests import logger
from mcp_tests import settings

LOG = logger.logger
LOG.addHandler(logger.console)


class SystemBaseTest(object):
    """SystemBaseTest contains setup/teardown for environment creation"""

    kube_settings = {}

    base_images = [
        "quay.io/coreos/etcd",
        "andyshinn/dnsmasq",
        "quay.io/coreos/hyperkube"
    ]

    def exec_on_node(self, env, node, cmd, expected_exit_code=0):
        """Function to exec command on node and get result

        :param env: mcp_tests.managers.envmanager.EnvironmentManager
        :param node: devops.models.Node
        :param cmd: string
        :rtype: dict
        """
        remote = env.node_ssh_client(
            node,
            **settings.SSH_NODE_CREDENTIALS
        )
        with remote.get_sudo(remote):
            result = remote.execute(
                command=cmd,
                verbose=True
            )
            assert result['exit_code'] == expected_exit_code
        return result

    def calico_ipip_exists(self, node, env):
        """Check if ipip is in calico pool config

        :param node: devops.models.Node
        :param env: mcp_tests.managers.envmanager.EnvironmentManager
        """
        for node in env.k8s_nodes:
            cmd = "calicoctl pool show | grep ipip"
            self.exec_on_node(env, node, cmd)

    def running_containers(self, node, env, network_plugin):
        """Check if there are all base containers on node

        :param node: devops.models.Node
        :param env: mcp_tests.managers.envmanager.EnvironmentManager
        """
        cmd = "docker ps --no-trunc --format '{{.Image}}'"
        expected_list = copy.deepcopy(self.base_images)
        if network_plugin == 'calico':
            expected_list.append('calico/node')
        result = self.exec_on_node(env, node, cmd)
        images = [x.split(":")[0] for x in result['stdout']]
        assert set(expected_list) < set(images)

    def check_running_containers(self, env, network_plugin=''):
        """Check running containers on each node

        :param env: mcp_tests.managers.envmanager.EnvironmentManager
        """
        for node in env.k8s_nodes:
            self.running_containers(node, env, network_plugin)

    def check_number_kube_nodes(self, env, k8sclient):
        """Check number of slaves"""
        LOG.info("Check number of nodes")
        k8s_nodes = k8sclient.nodes.list()
        devops_nodes = env.k8s_nodes
        assert len(k8s_nodes) == len(devops_nodes)

    def check_etcd_health(self, env):
        devops_nodes = env.k8s_nodes
        cmd = "etcdctl cluster-health | grep -c 'got healthy result'"
        etcd_nodes = self.exec_on_node(env, env.k8s_nodes[0], cmd)['stdout'][0]
        assert int(etcd_nodes) == len(devops_nodes),\
            "Number of etcd nodes is {0}," \
            " should be {1}".format(etcd_nodes, len(devops_nodes))

    def ccp_install_k8s(self, env, custom_yaml=None, env_var=None):
        """Action to deploy k8s by fuel-ccp-installer script

        :param env: mcp_tests.managers.envmanager.EnvironmentManager
        """
        current_env = copy.deepcopy(os.environ)
        environment_variables = {
            "SLAVE_IPS": " ".join(env.k8s_ips),
            "ADMIN_IP": env.k8s_ips[0],
        }
        if custom_yaml:
            environment_variables.update(
                {"CUSTOM_YAML": yaml.dump(
                    custom_yaml, default_flow_style=False)}
            )
        if env_var:
            environment_variables.update(env_var)
        current_env.update(dict=environment_variables)
        self.deploy_k8s(environ=current_env)

    def deploy_k8s(self, environ=os.environ):
        """Base action to deploy k8s by external deployment script"""
        try:
            process = subprocess.Popen([settings.DEPLOY_SCRIPT],
                                       env=environ,
                                       shell=True,
                                       bufsize=0,
                                       )
            assert process.wait() == 0
        except (SystemExit, KeyboardInterrupt) as err:
            process.terminate()
            raise err

    def create_env_snapshot(self, name, env, description=None):
        env.create_snapshot(name, description=description)

    @pytest.mark.skipif(not settings.SUSPEND_ENV_ON_TEARDOWN,
                        reason="Suspend isn't needed"
                        )
    @classmethod
    def teardown_class(cls, env):
        """Suspend environment"""
        LOG.info("Suspending environment")
        env.suspend()
