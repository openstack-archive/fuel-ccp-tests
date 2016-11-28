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

from fuel_ccp_tests import logger
from fuel_ccp_tests.helpers import post_install_k8s_checks


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

    def check_list_required_images(self, underlay, required_images):
        """Check running containers on each node

        :param underlay: fuel_ccp_tests.managers.UnderlaySSHManager
        :param required_images: list
        """
        LOG.info("Check that required containers exist")
        for node_name in underlay.node_names():
            post_install_k8s_checks.required_images_exists(node_name,
                                                           underlay,
                                                           required_images)

    def check_number_kube_nodes(self, underlay, k8sclient):
        """Check number of slaves"""
        LOG.info("Check number of nodes")
        k8s_nodes = k8sclient.nodes.list()
        node_names = underlay.node_names()
        assert len(k8s_nodes) == len(node_names),\
            "Check number k8s nodes failed!"

    def check_etcd_health(self, underlay):
        node_names = underlay.node_names()
        #TODO remove export after that issue will be fixed in KARGO
        cmd = "export ETCDCTL_ENDPOINT=https://127.0.0.1:2379;" \
              "etcdctl cluster-health | grep -c 'got healthy result'"

        etcd_nodes = underlay.sudo_check_call(
            cmd, node_name=node_names[0])['stdout'][0]
        assert int(etcd_nodes) == len(node_names),\
            "Number of etcd nodes is {0}," \
            " should be {1}".format(int(etcd_nodes), len(node_names))

    def create_env_snapshot(self, name, hardware, description=None):
        hardware.create_snapshot(name, description=description)
