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
        "quay.io/coreos/etcd",
    ]

    custom_yaml_images = base_images + [kube_settings['hyperkube_image_repo']]


class TestFuelCCPInstaller(base_test.SystemBaseTest,
                           FuelCCPInstallerConfigMixin):
    """Test class for testing k8s deployed by fuel-ccp-installer"""

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
        """
        self.ccp_install_k8s(env)
        self.check_number_kube_nodes(env, k8sclient)
        self.check_running_containers(env, required_images=self.base_images)
        self.calico_ipip_exists(env)
        self.check_etcd_health(env)

    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot
    @pytest.mark.fail_snapshot
    def test_k8s_installed_with_custom_yaml(self, env, k8sclient):
        """Test for deploying an k8s environment and check it

        Scenario:
            1. Install k8s.
            2. Check number of nodes.
            3. Basic check of running containers on nodes.
            4. Check requirement base settings.
        """
        self.ccp_install_k8s(env, custom_yaml=self.kube_settings)
        self.check_number_kube_nodes(env, k8sclient)
        self.check_running_containers(env,
                                      required_images=self.custom_yaml_images)
        self.calico_ipip_exists(env)
        self.check_etcd_health(env)

    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot
    @pytest.mark.fail_snapshot
    def test_k8s_installed_with_custom_yaml_etcd_on_host(self, env, k8sclient):
        """Test for deploying an k8s environment and check it

        Scenario:
            1. Install k8s with forced etcd on host.
            2. Check number of nodes.
            3. Basic check of running containers on nodes.
            4. Check requirement base settings.
        """
        kube_settings = dict()
        kube_settings.update(self.kube_settings)
        kube_settings.update({
            'etcd_deployment_type': 'host',
            'kube_network_plugin': 'calico'
        })
        required_images = filter(lambda x: 'etcd' not in x,
                                 self.custom_yaml_images)
        self.ccp_install_k8s(env, custom_yaml=kube_settings)
        self.check_number_kube_nodes(env, k8sclient)
        self.check_running_containers(env,
                                      required_images=required_images)
        self.calico_ipip_exists(env)
        self.check_etcd_health(env)

    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot
    @pytest.mark.fail_snapshot
    def test_k8s_installed_with_custom_yaml_etcd_in_container(self, env,
                                                              k8sclient):
        """Test for deploying an k8s environment and check it

        Scenario:
            1. Install k8s with forced etcd in container.
            2. Check number of nodes.
            3. Basic check of running containers on nodes.
            4. Check requirement base settings.
        """
        kube_settings = dict()
        kube_settings.update(self.kube_settings)
        kube_settings.update({
            'etcd_deployment_type': 'docker',
            'kube_network_plugin': 'calico'
        })
        self.ccp_install_k8s(env, custom_yaml=kube_settings)
        self.check_number_kube_nodes(env, k8sclient)
        self.check_running_containers(env,
                                      required_images=self.base_images)
        self.calico_ipip_exists(env)
        self.check_etcd_health(env)

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
        """
        add_var = {
            "WORKSPACE": ssh_keys_dir
        }
        self.ccp_install_k8s(env, env_var=add_var)
        self.check_number_kube_nodes(env, k8sclient)
        self.check_running_containers(env, required_images=self.base_images)
        self.calico_ipip_exists(env)
        self.check_etcd_health(env)
