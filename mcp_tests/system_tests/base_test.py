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
import yaml

import pytest

from devops.helpers import helpers

from mcp_tests import logger
from mcp_tests import settings

LOG = logger.logger
LOG.addHandler(logger.console)


class SystemBaseTest(object):
    """SystemBaseTest contains setup/teardown for environment creation"""

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
        return self.exec_on_remote(remote, cmd, expected_exit_code)

    def exec_on_remote(self, remote, cmd, expected_exit_code=0):
        with remote.get_sudo(remote):
            result = remote.execute(
                command=cmd,
                verbose=True
            )
            assert result['exit_code'] == expected_exit_code,\
                "Failed command '{}' run on node '{}'".format(
                    cmd, remote.hostname)
        return result

    def calico_ipip_exists(self, env):
        """Check if ipip is in calico pool config

        :param node: devops.models.Node
        :param env: mcp_tests.managers.envmanager.EnvironmentManager
        """
        cmd = "calicoctl pool show | grep ipip"
        for node in env.k8s_nodes:
            self.exec_on_node(env, node, cmd)

    def required_images_exists(self, node, env, required_images):
        """Check if there are all base containers on node

        :param node: devops.models.Node
        :param env: mcp_tests.managers.envmanager.EnvironmentManager
        :param required_images: list
        """
        cmd = "docker ps --no-trunc --format '{{.Image}}'"
        result = self.exec_on_node(env, node, cmd)
        images = [x.split(":")[0] for x in result['stdout']]
        assert set(required_images) < set(images),\
            "Running containers check failed on node '{}'".format(node.name)

    def check_list_required_images(self, env, required_images):
        """Check running containers on each node

        :param env: mcp_tests.managers.envmanager.EnvironmentManager
        :param required_images: list
        """
        LOG.info("Check that required containers exist")
        for node in env.k8s_nodes:
            self.required_images_exists(node, env, required_images)

    def check_pod_create(self, body, k8sclient, timeout=300, interval=5):
        """Check creating sample pod

        :param k8s_pod: V1Pod
        :param k8sclient: K8sCluster
        :rtype: V1Pod
        """
        LOG.info("Creating pod in k8s cluster")
        LOG.debug(
            "POD spec to create:\n{}".format(
                yaml.dump(body, default_flow_style=False))
        )
        LOG.debug("Timeout for creation is set to {}".format(timeout))
        LOG.debug("Checking interval is set to {}".format(interval))
        pod = k8sclient.pods.create(body=body)
        helpers.wait(
            predicate=lambda: k8sclient.pods.get(
                name=pod.metadata.name).status.phase == "Running",
            timeout=timeout,
            interval=interval,
            timeout_msg="Pod creation timeout reached!"
        )
        LOG.info("Pod '{}' is created".format(pod.metadata.name))
        return k8sclient.pods.get(name=pod.metadata.name)

    def check_pod_delete(self, k8s_pod, k8sclient):
        """Deleting pod from k8s

        :param k8s_pod: mcp_tests.models.k8s.pods.K8sPod
        :param k8sclient: mcp_tests.models.k8s.cluster.K8sCluster
        """
        LOG.info("Deleting pod '{}'".format(k8s_pod.name))
        LOG.debug("Pod status:\n{}".format(k8s_pod.status))
        k8sclient.pods.delete(body=k8s_pod.swagger_types, name=k8s_pod.name)
        LOG.debug("Pod '{}' is deleted".format(k8s_pod.name))

    def check_number_kube_nodes(self, env, k8sclient):
        """Check number of slaves"""
        LOG.info("Check number of nodes")
        k8s_nodes = k8sclient.nodes.list()
        devops_nodes = env.k8s_nodes
        assert len(k8s_nodes) == len(devops_nodes),\
            "Check number k8s nodes failed!"

    def check_etcd_health(self, env):
        devops_nodes = env.k8s_nodes
        cmd = "etcdctl cluster-health | grep -c 'got healthy result'"
        etcd_nodes = self.exec_on_node(env, env.k8s_nodes[0], cmd)['stdout'][0]
        assert int(etcd_nodes) == len(devops_nodes),\
            "Number of etcd nodes is {0}," \
            " should be {1}".format(int(etcd_nodes), len(devops_nodes))

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
