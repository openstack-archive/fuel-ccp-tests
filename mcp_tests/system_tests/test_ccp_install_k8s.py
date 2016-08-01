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

from mcp_tests import logger
from mcp_tests import settings
import base_test

LOG = logger.logger


class FuelCCPInstallerConfigMixin:

    kube_settings = {
        "ipip": settings.IPIP_USAGE,
        "hyperkube_image_repo": settings.HYPERKUBE_IMAGE_REPO,
        "hyperkube_image_tag": settings.HYPERKUBE_IMAGE_TAG,
        "docker_version": float(settings.DOCKER_VERSION),
        "kube_hostpath_dynamic_provisioner": "{}".format(
            settings.KUBE_HOSTPATH_DYNAMIC_PROVISIONER).lower(),
        "kube_version": settings.KUBE_VERSION,
    }

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

        :param k8s_node: mcp_tests.models.k8s.nodes.K8sNode
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
    def check_nginx_pod_is_reached(env, ip, node=None):
        """Simple check that nginx could be reached

        :param env: mcp_tests.managers.envmanager.EnvironmentManager
        :param ip: string
        :param node: devops.models.node.Node
        """
        env_node = node or env.k8s_nodes[0]
        remote = env.node_ssh_client(
            env_node,
            **settings.SSH_NODE_CREDENTIALS
        )
        cmd = "curl http://{}".format(ip)
        remote.check_call(command=cmd, verbose=True)

    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot
    @pytest.mark.fail_snapshot
    def test_k8s_installed_default(self, env, k8sclient):
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
        self.ccp_install_k8s(env)
        self.check_number_kube_nodes(env, k8sclient)
        self.check_list_required_images(env, required_images=self.base_images)
        self.calico_ipip_exists(env)
        self.check_etcd_health(env)
        nginx = self.get_nginx_spec()
        pod = self.check_pod_create(body=nginx, k8sclient=k8sclient)
        self.check_nginx_pod_is_reached(env, pod.status.pod_ip)
        self.check_pod_delete(pod, k8sclient)

    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot
    @pytest.mark.fail_snapshot
    def test_k8s_installed_with_etcd_on_host(self, env, k8sclient):
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
        self.ccp_install_k8s(env, custom_yaml=kube_settings)
        self.check_number_kube_nodes(env, k8sclient)
        self.check_list_required_images(env,
                                        required_images=required_images)
        self.calico_ipip_exists(env)
        self.check_etcd_health(env)
        nginx = self.get_nginx_spec()
        pod = self.check_pod_create(body=nginx, k8sclient=k8sclient)
        self.check_nginx_pod_is_reached(env, pod.status.pod_ip)
        self.check_pod_delete(pod, k8sclient)

    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot
    @pytest.mark.fail_snapshot
    def test_k8s_installed_with_etcd_in_container(self, env,
                                                  k8sclient):
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
        self.ccp_install_k8s(env, custom_yaml=kube_settings)
        self.check_number_kube_nodes(env, k8sclient)
        self.check_list_required_images(env,
                                        required_images=required_images)
        self.calico_ipip_exists(env)
        self.check_etcd_health(env)
        nginx = self.get_nginx_spec()
        pod = self.check_pod_create(body=nginx, k8sclient=k8sclient)
        self.check_nginx_pod_is_reached(env, pod.status.pod_ip)
        self.check_pod_delete(pod, k8sclient)

    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot
    @pytest.mark.fail_snapshot
    def test_k8s_installed_with_ready_ssh_keys(self, ssh_keys_dir, env,
                                               k8sclient):
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
        self.ccp_install_k8s(env, env_var=add_var)
        self.check_number_kube_nodes(env, k8sclient)
        self.check_list_required_images(env, required_images=self.base_images)
        self.calico_ipip_exists(env)
        self.check_etcd_health(env)
        nginx = self.get_nginx_spec()
        pod = self.check_pod_create(body=nginx, k8sclient=k8sclient)
        self.check_nginx_pod_is_reached(env, pod.status.pod_ip)
        self.check_pod_delete(pod, k8sclient)
