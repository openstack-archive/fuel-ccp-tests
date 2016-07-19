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
import logging
import subprocess
import os

import pytest
import yaml

from mcp_tests import logger
from mcp_tests import settings

logging.getLogger('EnvironmentManager').addHandler(logger.console)

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

    def running_containers(self, node, env):
        """Check if there are all base containers on node

        :param node: devops.models.Node
        """
        remote = env.node_ssh_client(
            node,
            **settings.SSH_NODE_CREDENTIALS
        )
        cmd = "docker ps --no-trunc --format '{{.Image}}'"
        with remote.get_sudo(remote):
            result = remote.execute(
                command=cmd,
                verbose=True
            )
            assert result['exit_code'] == 0
        images = [x.split(":")[0] for x in result['stdout']]
        assert set(self.base_images) < set(images)

    def check_running_containers(self, env):
        for node in env.k8s_nodes:
            self.running_containers(node, env)

    def check_number_kube_nodes(self, env, k8sclient):
        """Check number of slaves"""
        LOG.info("Check number of nodes")
        k8s_nodes = k8sclient.nodes.list()
        devops_nodes = env.k8s_nodes
        assert len(k8s_nodes) == len(devops_nodes)

    def ccp_install_k8s(self, env, use_custom_yaml=False):
        current_env = copy.deepcopy(os.environ)
        environment_variables = {
            "SLAVE_IPS": " ".join(env.k8s_ips),
            "ADMIN_IP": env.k8s_ips[0],
        }
        if use_custom_yaml:
            environment_variables.update(
                {"CUSTOM_YAML": yaml.dump(
                    self.kube_settings, default_flow_style=False)}
            )
            network_plugin = self.kube_settings.get(
                'kube_network_plugin', None)
            if network_plugin == 'calico':
                self.base_images.append('calico/node')
        current_env.update(dict=environment_variables)
        try:
            process = subprocess.Popen([settings.DEPLOY_SCRIPT],
                                       env=current_env,
                                       shell=True,
                                       bufsize=0,
                                       )
            assert process.wait() == 0
        except (SystemExit, KeyboardInterrupt) as err:
            process.terminate()
            raise err

    def deploy_k8s(self):
        try:
            process = subprocess.Popen([settings.DEPLOY_SCRIPT],
                                       env=os.environ,
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
