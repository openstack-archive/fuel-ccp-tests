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
from mcp_tests.helpers import utils
import base_test

LOG = logger.logger


class TestFuelCCPInstallerDefault(base_test.SystemBaseTest):
    """Test class for testing k8s deployed by fuel-ccp-installer"""

    default_lable = 'test_default_k8s_installation'

    base_images = [
        "andyshinn/dnsmasq",
        "quay.io/coreos/hyperkube"
    ]

    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot
    @pytest.mark.fail_snapshot
    @pytest.mark.lable(name=default_lable)
    def test_k8s_installed(self, env, k8sclient):
        """Test for deploying an k8s environment and check it

        Scenario:
            1. Install k8s.
            2. Check number of nodes.
            3. Basic check of running containers on nodes.
            4. Check requirement base settings.
        """
        self.ccp_install_k8s(env)
        self.check_number_kube_nodes(env, k8sclient)
        self.check_running_containers(env)
        self.check_requirement_settings(env)


class TestFuelCCPInstallerCustom(TestFuelCCPInstallerDefault):

    default_lable = 'test_k8s_with_custom_yaml'

    kube_settings = {
        # Configure calico to set --nat-outgoing and --ipip pool option	18
        "ipip": settings.IPIP_USAGE,
        "hyperkube_image_repo": "gcr.io/google_containers/hyperkube",
        "hyperkube_image_tag": settings.KUBE_VERSION,
        "docker_version": float(settings.DOCKER_VERSION),
        "kube_hostpath_dynamic_provisioner": "true",
        "kube_version": settings.KUBE_VERSION,
    }

    base_images = [
        "andyshinn/dnsmasq",
        "calico/node",
        "quay.io/coreos/etcd",
        kube_settings['hyperkube_image_repo'],
    ]


class TestFuelCCPInstallerCustomWithSSHKeys(TestFuelCCPInstallerCustom):

    default_lable = 'test_k8s_with_custom_yaml_and_ssh_keys'

    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot
    @pytest.mark.fail_snapshot
    @pytest.mark.lable(name=default_lable)
    def test_k8s_installed(self, ssh_keys_dir, env, k8sclient):
        """Test for deploying an k8s environment and check it

        Scenario:
            1. Install k8s (with prepared ssh keys).
            2. Check number of nodes.
            3. Basic check of running containers on nodes.
            4. Check requirement base settings.
        """
        try:
            super(
                TestFuelCCPInstallerCustomWithSSHKeys,
                self).test_k8s_installed(env, k8sclient)
        except AssertionError as err:
            utils.clean_dir(ssh_keys_dir)
            raise err
