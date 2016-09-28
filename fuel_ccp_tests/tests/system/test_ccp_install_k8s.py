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

import pytest

import base_test
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import ext


class FuelCCPInstallerConfigMixin:

    kube_settings = settings.DEFAULT_CUSTOM_YAML

    base_images = [
        "andyshinn/dnsmasq",
        "calico/node",
    ]

    custom_yaml_images = base_images + [kube_settings['hyperkube_image_repo']]


@pytest.mark.fuel_ccp_installer
@pytest.mark.system
class TestFuelCCPInstaller(base_test.SystemBaseTest,
                           FuelCCPInstallerConfigMixin):
    """Test class for testing k8s deployed by fuel-ccp-installer

       pytest.mark: fuel_ccp_installer
    """

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

    @pytest.mark.k8s_installed_default
    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.underlay)
    @pytest.mark.fail_snapshot
    def test_k8s_installed_default(self, underlay, k8s_actions):
        """Test for deploying an k8s environment and check it

        pytest.mark: k8s_installed_default

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
        k8sclient = k8s_actions.api

        self.check_number_kube_nodes(underlay, k8sclient)
        self.check_list_required_images(
            underlay, required_images=self.base_images)
        self.check_etcd_health(underlay)
        nginx = self.get_nginx_spec()
        pod = k8s_actions.check_pod_create(body=nginx)
        self.check_nginx_pod_is_reached(underlay, pod.status.pod_ip)
        k8s_actions.check_pod_delete(pod)

    @pytest.mark.k8s_installed_custom
    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.underlay)
    @pytest.mark.fail_snapshot
    @pytest.mark.bvt
    def test_k8s_installed_custom(self, underlay, k8s_actions, show_step):
        """Test for deploying an k8s environment with custom parameters
        and check it

        Scenario:
            1. Install k8s with custom parameters
            2. Check number of nodes.
            3. Basic check of running containers on nodes.
            4. Check etcd health.
            5. Create nginx pod.
            6. Check created pod is reached.
            7. Delete pod.

        Duration: 1200
        """
        show_step(1)
        k8s_actions.install_k8s(self.kube_settings)
        k8sclient = k8s_actions.api

        show_step(2)
        self.check_number_kube_nodes(underlay, k8sclient)

        show_step(3)
        self.check_list_required_images(
            underlay, required_images=self.base_images)

        show_step(4)
        self.check_etcd_health(underlay)

        show_step(5)
        nginx = self.get_nginx_spec()
        pod = k8s_actions.check_pod_create(body=nginx)

        show_step(6)
        self.check_nginx_pod_is_reached(underlay, pod.status.pod_ip)

        show_step(7)
        k8s_actions.check_pod_delete(pod)

    @pytest.mark.k8s_installed_with_etcd_on_host
    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.underlay)
    @pytest.mark.fail_snapshot
    def test_k8s_installed_with_etcd_on_host(self, underlay, k8s_actions):
        """Test for deploying an k8s environment and check it

        pytest.mark: k8s_installed_with_etcd_on_host

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
        k8sclient = k8s_actions.api

        self.check_number_kube_nodes(underlay, k8sclient)
        self.check_list_required_images(underlay,
                                        required_images=required_images)
        self.check_etcd_health(underlay)
        nginx = self.get_nginx_spec()
        pod = k8s_actions.check_pod_create(body=nginx)
        self.check_nginx_pod_is_reached(underlay, pod.status.pod_ip)
        k8s_actions.check_pod_delete(pod)

    @pytest.mark.k8s_installed_with_etcd_in_container
    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.underlay)
    @pytest.mark.fail_snapshot
    def test_k8s_installed_with_etcd_in_container(self, underlay, k8s_actions):
        """Test for deploying an k8s environment and check it

        pytest.mark: k8s_installed_with_etcd_in_container

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
        k8sclient = k8s_actions.api

        self.check_number_kube_nodes(underlay, k8sclient)
        self.check_list_required_images(underlay,
                                        required_images=required_images)
        self.check_etcd_health(underlay)
        nginx = self.get_nginx_spec()
        pod = k8s_actions.check_pod_create(body=nginx)
        self.check_nginx_pod_is_reached(underlay, pod.status.pod_ip)
        k8s_actions.check_pod_delete(pod)

    @pytest.mark.k8s_installed_with_ready_ssh_keys
    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.underlay)
    @pytest.mark.fail_snapshot
    def test_k8s_installed_with_ready_ssh_keys(self, ssh_keys_dir,
                                               underlay, k8s_actions):
        """Test for deploying an k8s environment and check it

        pytest.mark: k8s_installed_with_ready_ssh_keys

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
        k8sclient = k8s_actions.api

        self.check_number_kube_nodes(underlay, k8sclient)
        self.check_list_required_images(
            underlay, required_images=self.base_images)
        self.check_etcd_health(underlay)
        nginx = self.get_nginx_spec()
        pod = k8s_actions.check_pod_create(body=nginx)
        self.check_nginx_pod_is_reached(underlay, pod.status.pod_ip)
        k8s_actions.check_pod_delete(pod)

    @pytest.mark.test_k8s_installed_with_ipip
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.underlay)
    @pytest.mark.fail_snapshot
    def test_k8s_installed_with_ipip(self, underlay, k8s_actions, show_step):
        """Test for deploying an k8s environment with IPIP tunnels for Calico
           and check it

        Scenario:
            1. Enable 'ipip' in the settings
            2. Install k8s.
            3. Check Calico IPIP tunnels exist
            4. Basic check of running containers on nodes.
            5. Create nginx pod.
            6. Check created pod is reached
            7. Delete pod.

        Duration: 1200
        """
        show_step(1)
        custom_yaml = copy.deepcopy(self.kube_settings)
        custom_yaml['ipip'] = True

        show_step(2)
        k8s_actions.install_k8s(custom_yaml=custom_yaml)

        show_step(3)
        self.calico_ipip_exists(underlay)

        show_step(4)
        self.check_list_required_images(
            underlay, required_images=self.base_images)

        show_step(5)
        nginx = self.get_nginx_spec()
        pod = k8s_actions.check_pod_create(body=nginx)

        show_step(6)
        self.check_nginx_pod_is_reached(underlay, pod.status.pod_ip)

        show_step(7)
        k8s_actions.check_pod_delete(pod)


@pytest.mark.fuel_ccp_installer_idempotency
@pytest.mark.system
class TestFuelCCPInstallerIdempotency(base_test.SystemBaseTest,
                                      FuelCCPInstallerConfigMixin):

    @staticmethod
    def get_ansible_changes_count(stdout_str):
        offset = 0
        result = 0
        while "changed=" in stdout_str[offset:]:
            offset = stdout_str.find("changed=", offset) + 8
            changed = stdout_str[offset: stdout_str.find(" ", offset)]
            result += int(changed)
        return result

    @pytest.mark.ccp_idempotency_default
    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.underlay)
    @pytest.mark.fail_snapshot
    def test_k8s_ccp_idempotency_default(self, config, underlay, k8s_actions):
        """Test for deploying an k8s environment and check it

        pytest.mark: k8s_installed_default

        Scenario:
            1. Install k8s.
            2. Check that count of changes in the ansible log is more than 0
            3. Re-install k8s.
            4. Check that count of changes in the ansible log is 0
        """
        result = k8s_actions.install_k8s(verbose=False)
        changed = self.get_ansible_changes_count(result.stdout_str)
        assert changed != 0, "No changes during k8s install!"
        result = k8s_actions.install_k8s(verbose=False)
        changed = self.get_ansible_changes_count(result.stdout_str)
        assert changed == 0, (
            "Should be no changes during the second install "
            "of k8s while there are '{0}' changes!".format(changed))

    @pytest.mark.ccp_idempotency_with_etcd_on_host
    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.underlay)
    @pytest.mark.fail_snapshot
    def test_ccp_idempotency_with_etcd_on_host(self, config, underlay,
                                               k8s_actions):
        """Test for deploying an k8s environment and check it

        pytest.mark: k8s_installed_with_etcd_on_host

        Scenario:
            1. Install k8s with forced etcd on host.
            2. Check that count of changes in the ansible log is more than 0
            3. Re-install k8s with forced etcd on host.
            4. Check that count of changes in the ansible log is 0
        """
        kube_settings = dict()
        kube_settings.update(self.kube_settings)
        kube_settings.update({
            'etcd_deployment_type': 'host',
            'kube_network_plugin': 'calico'
        })
        result = k8s_actions.install_k8s(custom_yaml=kube_settings,
                                         verbose=False)
        changed = self.get_ansible_changes_count(result.stdout_str)
        assert changed != 0, "No changes during k8s install!"
        result = k8s_actions.install_k8s(custom_yaml=kube_settings,
                                         verbose=False)
        changed = self.get_ansible_changes_count(result.stdout_str)
        assert changed == 0, (
            "Should be no changes during the second install "
            "of k8s while there are '{0}' changes!".format(changed))

    @pytest.mark.ccp_idempotency_with_etcd_in_container
    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.underlay)
    @pytest.mark.fail_snapshot
    def test_ccp_idempotency_with_etcd_in_container(self, config, underlay,
                                                    k8s_actions):
        """Test for deploying an k8s environment and check it

        pytest.mark: k8s_installed_with_etcd_in_container

        Scenario:
            1. Install k8s with forced etcd in container.
            2. Check that count of changes in the ansible log is more than 0
            3. Re-install k8s with forced etcd in container.
            4. Check that count of changes in the ansible log is 0
        """
        kube_settings = dict()
        kube_settings.update(self.kube_settings)
        kube_settings.update({
            'etcd_deployment_type': 'docker',
            'kube_network_plugin': 'calico',
            'etcd_image_repo': settings.ETCD_IMAGE_REPO,
            'etcd_image_tag': settings.ETCD_IMAGE_TAG,
        })
        result = k8s_actions.install_k8s(custom_yaml=kube_settings,
                                         verbose=False)
        changed = self.get_ansible_changes_count(result.stdout_str)
        assert changed != 0, "No changes during k8s install!"
        result = k8s_actions.install_k8s(custom_yaml=kube_settings,
                                         verbose=False)
        changed = self.get_ansible_changes_count(result.stdout_str)
        assert changed == 0, (
            "Should be no changes during the second install "
            "of k8s while there are '{0}' changes!".format(changed))

    @pytest.mark.ccp_idempotency_with_ready_ssh_keys
    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.underlay)
    @pytest.mark.fail_snapshot
    def test_ccp_idempotency_with_ready_ssh_keys(self, ssh_keys_dir,
                                                 config, underlay,
                                                 k8s_actions):
        """Test for deploying an k8s environment and check it

        pytest.mark: k8s_installed_with_ready_ssh_keys

        Scenario:
            1. Install k8s (with prepared ssh keys).
            2. Check that count of changes in the ansible log is more than 0
            3. Re-install k8s (with prepared ssh keys).
            4. Check that count of changes in the ansible log is 0
        """
        add_var = {
            "WORKSPACE": ssh_keys_dir
        }
        result = k8s_actions.install_k8s(env_var=add_var,
                                         verbose=False)
        changed = self.get_ansible_changes_count(result.stdout_str)
        assert changed != 0, "No changes during k8s install!"
        result = k8s_actions.install_k8s(env_var=add_var,
                                         verbose=False)
        changed = self.get_ansible_changes_count(result.stdout_str)
        assert changed == 0, (
            "Should be no changes during the second install "
            "of k8s while there are '{0}' changes!".format(changed))
