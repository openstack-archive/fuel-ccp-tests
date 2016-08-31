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

import base_test
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import ext

LOG = logger.logger


class FuelCCPInstallerConfigMixin:

    kube_settings = settings.DEFAULT_CUSTOM_YAML

    base_images = [
        "andyshinn/dnsmasq",
        "calico/node",
    ]

    custom_yaml_images = base_images + [kube_settings['hyperkube_image_repo']]


class TestFuelCCPInstaller(base_test.SystemBaseTest,
                           FuelCCPInstallerConfigMixin):
    """Test class for testing k8s deployed by fuel-ccp-installer"""

    @staticmethod
    def get_nginx_spec(k8s_node=None):
        """Create spec for k8s pod creation

        :param k8s_node: fuel_ccp_tests.managers.k8s.nodes.K8sNode
        """
        pod = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"name": "nginx"},
            "spec": {
                "containers": [
                    {"name": "nginx",
                     "image": "nginx",
                     "ports": [{"containerPort": 80}]}
                ],
            }
        }
        if k8s_node:
            pod['spec']['nodeName'] = k8s_node.name
        return pod

    @staticmethod
    def check_nginx_pod_is_reached(underlay, ip, node_name=None):
        """Simple check that nginx could be reached

        :param underlay: fuel_ccp_tests.managers.UnderlaySSHManager
        :param ip: string
        :param node_name: string
        """
        env_node = node_name or underlay.node_names()[0]
        cmd = "curl http://{}".format(ip)
        underlay.sudo_check_call(cmd=cmd, node_name=env_node, verbose=True)

    @pytest.mark.snapshot_needed
    @pytest.mark.fail_snapshot
    def test_k8s_installed_default(self, underlay, k8s_actions):
        """Test for deploying an k8s environment and check it

        Scenario:
            1. Install k8s.
            2. Check number of nodes.
            3. Basic check of running containers on nodes.
            4. Check requirement base settings.
            5. Create nginx pod.
            6. Check created pod is reached
            7. Delete pod.
        """
        k8s_actions.install_k8s()
        k8sclient = k8s_actions.get_k8sclient()

        self.check_number_kube_nodes(underlay, k8sclient)
        self.check_list_required_images(
            underlay, required_images=self.base_images)
        self.calico_ipip_exists(underlay)
        self.check_etcd_health(underlay)
        nginx = self.get_nginx_spec()
        pod = self.check_pod_create(body=nginx, k8sclient=k8sclient)
        self.check_nginx_pod_is_reached(underlay, pod.status.pod_ip)
        self.check_pod_delete(pod, k8sclient)

    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.underlay)
    @pytest.mark.fail_snapshot
    def test_k8s_installed_with_etcd_on_host(self, underlay, k8s_actions):
        """Test for deploying an k8s environment and check it

        Scenario:
            1. Install k8s with forced etcd on host.
            2. Check number of nodes.
            3. Basic check of running containers on nodes.
            4. Check requirement base settings.
            5. Create nginx pod.
            6. Check created pod is reached
            7. Delete pod.
        """
        kube_settings = dict()
        kube_settings.update(self.kube_settings)
        kube_settings.update({
            'etcd_deployment_type': 'host',
            'kube_network_plugin': 'calico'
        })
        required_images = filter(
            lambda x: x != kube_settings.get(
                'etcd_image_repo', settings.ETCD_IMAGE_REPO),
            self.custom_yaml_images)

        k8s_actions.install_k8s(custom_yaml=kube_settings)
        k8sclient = k8s_actions.get_k8sclient()

        self.check_number_kube_nodes(underlay, k8sclient)
        self.check_list_required_images(underlay,
                                        required_images=required_images)
        self.calico_ipip_exists(underlay)
        self.check_etcd_health(underlay)
        nginx = self.get_nginx_spec()
        pod = self.check_pod_create(body=nginx, k8sclient=k8sclient)
        self.check_nginx_pod_is_reached(underlay, pod.status.pod_ip)
        self.check_pod_delete(pod, k8sclient)

    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.underlay)
    @pytest.mark.fail_snapshot
    def test_k8s_installed_with_etcd_in_container(self, underlay, k8s_actions):
        """Test for deploying an k8s environment and check it

        Scenario:
            1. Install k8s with forced etcd in container.
            2. Check number of nodes.
            3. Basic check of running containers on nodes.
            4. Check requirement base settings.
            5. Create nginx pod.
            6. Check created pod is reached
            7. Delete pod.
        """
        kube_settings = dict()
        kube_settings.update(self.kube_settings)
        kube_settings.update({
            'etcd_deployment_type': 'docker',
            'kube_network_plugin': 'calico',
            'etcd_image_repo': settings.ETCD_IMAGE_REPO,
            'etcd_image_tag': settings.ETCD_IMAGE_TAG,
        })
        required_images = list(self.base_images)
        required_images.append(kube_settings['etcd_image_repo'])

        k8s_actions.install_k8s(custom_yaml=kube_settings)
        k8sclient = k8s_actions.get_k8sclient()

        self.check_number_kube_nodes(underlay, k8sclient)
        self.check_list_required_images(underlay,
                                        required_images=required_images)
        self.calico_ipip_exists(underlay)
        self.check_etcd_health(underlay)
        nginx = self.get_nginx_spec()
        pod = self.check_pod_create(body=nginx, k8sclient=k8sclient)
        self.check_nginx_pod_is_reached(underlay, pod.status.pod_ip)
        self.check_pod_delete(pod, k8sclient)

    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.underlay)
    @pytest.mark.fail_snapshot
    def test_k8s_installed_with_ready_ssh_keys(self, ssh_keys_dir,
                                               underlay, k8s_actions):
        """Test for deploying an k8s environment and check it

        Scenario:
            1. Install k8s (with prepared ssh keys).
            2. Check number of nodes.
            3. Basic check of running containers on nodes.
            4. Check requirement base settings.
            5. Create nginx pod.
            6. Check created pod is reached
            7. Delete pod.
        """
        add_var = {
            "WORKSPACE": ssh_keys_dir
        }

        k8s_actions.install_k8s(env_var=add_var)
        k8sclient = k8s_actions.get_k8sclient()

        self.check_number_kube_nodes(underlay, k8sclient)
        self.check_list_required_images(
            underlay, required_images=self.base_images)
        self.calico_ipip_exists(underlay)
        self.check_etcd_health(underlay)
        nginx = self.get_nginx_spec()
        pod = self.check_pod_create(body=nginx, k8sclient=k8sclient)
        self.check_nginx_pod_is_reached(underlay, pod.status.pod_ip)
        self.check_pod_delete(pod, k8sclient)
