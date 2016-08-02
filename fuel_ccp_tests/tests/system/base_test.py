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

from devops.helpers import helpers
import pytest
import yaml

from fuel_ccp_tests import logger
from fuel_ccp_tests import settings

LOG = logger.logger
LOG.addHandler(logger.console)


class SystemBaseTest(object):
    """SystemBaseTest contains setup/teardown for environment creation"""

    def calico_ipip_exists(self, underlay):
        """Check if ipip is in calico pool config

        :param underlay: fuel_ccp_tests.managers.UnderlaySSHManager
        """
        cmd = "calicoctl pool show | grep ipip"
        for node_name in underlay.node_names():
            underlay.sudo_check_call(cmd, node_name=node_name)

    def required_images_exists(self, node_name, underlay, required_images):
        """Check if there are all base containers on node

        :param node_name: string
        :param underlay: fuel_ccp_tests.managers.UnderlaySSHManager
        :param required_images: list
        """
        cmd = "docker ps --no-trunc --format '{{.Image}}'"
        result = underlay.sudo_check_call(cmd, node_name=node_name)
        images = [x.split(":")[0] for x in result['stdout']]
        assert set(required_images) < set(images),\
            "Running containers check failed on node '{}'".format(node_name)

    def check_list_required_images(self, underlay, required_images):
        """Check running containers on each node

        :param underlay: fuel_ccp_tests.managers.UnderlaySSHManager
        :param required_images: list
        """
        LOG.info("Check that required containers exist")
        for node_name in underlay.node_names():
            self.required_images_exists(node_name, underlay, required_images)

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

        :param k8s_pod: fuel_ccp_tests.managers.k8s.nodes.K8sNode
        :param k8sclient: fuel_ccp_tests.managers.k8s.cluster.K8sCluster
        """
        LOG.info("Deleting pod '{}'".format(k8s_pod.name))
        LOG.debug("Pod status:\n{}".format(k8s_pod.status))
        k8sclient.pods.delete(body=k8s_pod.swagger_types, name=k8s_pod.name)
        LOG.debug("Pod '{}' is deleted".format(k8s_pod.name))

    def check_number_kube_nodes(self, underlay, k8sclient):
        """Check number of slaves"""
        LOG.info("Check number of nodes")
        k8s_nodes = k8sclient.nodes.list()
        node_names = underlay.node_names()
        assert len(k8s_nodes) == len(node_names),\
            "Check number k8s nodes failed!"

    def check_etcd_health(self, underlay):
        node_names = underlay.node_names()
        cmd = "etcdctl cluster-health | grep -c 'got healthy result'"

        etcd_nodes = underlay.sudo_check_call(
            cmd, node_name=node_names[0])['stdout'][0]
        assert int(etcd_nodes) == len(node_names),\
            "Number of etcd nodes is {0}," \
            " should be {1}".format(int(etcd_nodes), len(node_names))

    def create_env_snapshot(self, name, hardware, description=None):
        hardware.create_snapshot(name, description=description)

    @pytest.mark.skipif(not settings.SUSPEND_ENV_ON_TEARDOWN,
                        reason="Suspend isn't needed"
                        )
    @classmethod
    def teardown_class(cls, hardware):
        """Suspend environment"""
        LOG.info("Suspending environment")
        hardware.suspend()
