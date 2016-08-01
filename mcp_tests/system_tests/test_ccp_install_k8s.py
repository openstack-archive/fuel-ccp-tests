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


class TestFuelCCPInstaller(base_test.SystemBaseTest):
    """Test class for testing k8s deployed by fuel-ccp-installer"""

    kube_settings = {
        "kube_network_plugin": "calico",
        "kube_proxy_mode": "iptables",
        "hyperkube_image_repo": "quay.io/coreos/hyperkube",
        "hyperkube_image_tag": "{0}_coreos.0".format(settings.KUBE_VERSION),
        "kube_version": settings.KUBE_VERSION,
        # Configure calico to set --nat-outgoing and --ipip pool option	18
        "ipip": settings.IPIP_USAGE,
        "kube_version": settings.KUBE_VERSION
    }

    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot
    @pytest.mark.fail_snapshot
    def test_k8s_installed_default(self, env, k8sclient,
                                   use_custom_yaml=False):
        """Test for deploying an k8s environment and check it

        Scenario:
            1. Install k8s with default parameters.
            2. Check number of nodes.
            3. Basic check of running containers on nodes.
            4. Check requirement base settings.
        """
        self.ccp_install_k8s(env, use_custom_yaml=use_custom_yaml)
        self.check_number_kube_nodes(env, k8sclient)
        self.check_running_containers(env, use_custom_yaml=use_custom_yaml)
        self.check_requirement_settings(env, use_custom_yaml=use_custom_yaml)

    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot
    @pytest.mark.fail_snapshot
    def test_k8s_installed_with_custom_yaml(self, env, k8sclient,
                                            use_custom_yaml=True):
        """Test for deploying an k8s environment and check it

        Scenario:
            1. Install k8s with custom yaml.
            2. Check number of nodes.
            3. Basic check of running containers on nodes.
            4. Check requirement base settings.
        """
        self.ccp_install_k8s(env, use_custom_yaml=use_custom_yaml)
        self.check_number_kube_nodes(env, k8sclient)
        self.check_running_containers(env, use_custom_yaml=use_custom_yaml)
        self.check_requirement_settings(env, use_custom_yaml=use_custom_yaml)
