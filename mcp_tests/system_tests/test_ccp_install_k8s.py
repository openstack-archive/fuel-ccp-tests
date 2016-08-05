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

from mcp_tests import logger
from mcp_tests import settings
from mcp_tests.helpers import utils
import base_test

LOG = logger.logger


class TestFuelCCPInstaller(base_test.SystemBaseTest):
    """Test class for testing k8s deployed by fuel-ccp-installer"""

    kube_settings = {
        "kube_proxy_mode": "iptables",
        "hyperkube_image_repo": "quay.io/coreos/hyperkube",
        "hyperkube_image_tag": "{0}_coreos.0".format(
            settings.KUBE_VERSION),
        "kube_version": settings.KUBE_VERSION,
        "cloud_provider": "generic",
        # Configure calico to set --nat-outgoing and --ipip pool option	18
        "ipip": settings.IPIP_USAGE,
    }

    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot
    @pytest.mark.fail_snapshot
    def test_k8s_installed_default(self, env, k8sclient):
        """Test for deploying an k8s environment and check it

        Scenario:
            1. Install k8s with default parameters.
            2. Check number of nodes.
            3. Basic check of running containers on nodes.
            4. Check requirement base settings.
        """
        env.install_k8s(env)
        self.check_number_kube_nodes(env, k8sclient)
        self.check_running_containers(env)
        self.check_etcd_health(env)

    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot
    @pytest.mark.fail_snapshot
    def test_k8s_installed_with_etcd_on_host(self, env, k8sclient):
        """Deploy k8s with etcd on the host

        Scenario:
            1. Install k8s with custom yaml, etcd on the host
            2. Check number of nodes.
            3. Basic check of running containers on nodes.
            4. Check requirement base settings.
        """
        test_kube_settings = copy.deepcopy(self.kube_settings)
        additional_kube_settings = {
            "kube_network_plugin": "calico",
            "etcd_deployment_type": "host",
        }
        test_kube_settings.update(additional_kube_settings)
        env.install_k8s(env, custom_yaml=test_kube_settings)
        self.check_number_kube_nodes(env, k8sclient)
        self.check_running_containers(env, network_plugin='calico')
        self.calico_ipip_exists(env)
        self.check_etcd_health(env)

    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot
    @pytest.mark.fail_snapshot
    def test_k8s_installed_with_etcd_in_container(self, env, k8sclient):
        """Deploy k8s with etcd in container

        Scenario:
            1. Install k8s with custom yaml, etcd in container
            2. Check number of nodes.
            3. Basic check of running containers on nodes.
            4. Check requirement base settings.
        """
        test_kube_settings = copy.deepcopy(self.kube_settings)
        additional_kube_settings = {
            "kube_network_plugin": "calico",
            "etcd_deployment_type": "docker",
        }
        test_kube_settings.update(additional_kube_settings)
        env.install_k8s(env, custom_yaml=test_kube_settings)

        self.check_number_kube_nodes(env, k8sclient)
        self.check_running_containers(env, network_plugin='calico')
        self.calico_ipip_exists(env)
        self.check_etcd_health(env)

    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot
    @pytest.mark.fail_snapshot
    def test_k8s_installed_with_ready_ssh_keys(self, env, k8sclient):
        """Deploy k8s with ssh keys provided

        Scenario:
            1. Install k8s with ready ssh keys
            2. Check number of nodes.
            3. Basic check of running containers on nodes
        """
        dirpath = utils.generate_keys()
        env_var = {"WORKSPACE": dirpath}
        env.install_k8s(env, env_var=env_var)

        self.check_number_kube_nodes(env, k8sclient)
        self.check_running_containers(env, network_plugin='calico')
        utils.clean_dir(dirpath)
