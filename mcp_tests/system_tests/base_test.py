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

import logging
import subprocess
import os

import pytest

from mcp_tests import logger
from mcp_tests import settings

logging.getLogger('EnvironmentManager').addHandler(logger.console)

LOG = logger.logger

LOG.addHandler(logger.console)


class SystemBaseTest(object):
    """SystemBaseTest contains setup/teardown for environment creation"""

    base_images = [
        "calico/node",
        "andyshinn/dnsmasq",
        "quay.io/coreos/hyperkube"
    ]

    def running_containers(self, node):
        """Check if there are all base containers on node

        :param node: devops.models.Node
        """
        remote = self.env.node_ssh_client(
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

    def check_number_kube_nodes(self):
        """Check number of slaves"""
        LOG.info("Check number of nodes")
        master = self.env.k8s_nodes[0]
        remote = self.env.node_ssh_client(
            master,
            **settings.SSH_NODE_CREDENTIALS
        )
        cmd = "kubectl get nodes -o jsonpath={.items[*].metadata.name}"
        result = remote.execute(command=cmd, verbose=True)
        assert result["exit_code"] == 0, "Error: {0}".format(
            "".join(result["stderr"])
        )
        k8s_nodes = result["stdout_str"].split()
        devops_nodes = self.env.k8s_nodes
        assert len(k8s_nodes) == len(devops_nodes)

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

    def create_env_snapshot(self, name, description=None):
        self.env.create_snapshot(name, description=description)

    @pytest.mark.skipif(not settings.SUSPEND_ENV_ON_TEARDOWN,
                        reason="Suspend isn't needed"
                        )
    @classmethod
    def teardown_class(cls):
        """Suspend environment"""
        LOG.info("Suspending environment")
        cls.env.suspend()
