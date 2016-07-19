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

PARAMS = [False, True]
IDS = ["default", "with_custom_yaml"]


# Next fixture overrides existing one to parametrize k8s installation,
# there will be two installations without and with CUSTOM_YAML and
# after test there will be some snapshots, something like that:
# $ dos.py snapshot-list env
# SNAPSHOT
# ----------------------------------------------
# env_initial
# env_test_k8s_installed_default_failed
# env_test_k8s_installed_with_custom_yaml_passed
@pytest.fixture(params=PARAMS, ids=IDS)
def use_custom_yaml(request):
    """Fixture for parametrize k8s deployment with and without custom yaml"""
    setattr(request.node.function, '_snapshot_name',
            "{0}_{1}".format(
                request.node.function.__name__,
                IDS[request.param_index])
            )
    return request.param


class TestFuelCCPInstaller(base_test.SystemBaseTest):
    """Test class for testing k8s deployed by fuel-ccp-installer"""

    kube_settings = {
        "kube_network_plugin": "calico",
        "kube_proxy_mode": "iptables",
        "kube_version": settings.KUBE_VERSION,
        "cloud_provider": "generic"
    }

    # TODO(slebedev): Extend checks for k8s installation
    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot
    @pytest.mark.fail_snapshot
    def test_k8s_installed(self, env, k8sclient, use_custom_yaml):
        """Test for deploying an k8s environment and check it

        Scenario:
            1. Install k8s.
            2. Check number of nodes.
            3. Basic check of running containers on nodes.
            4. Check requirement base settings.
        """
        self.ccp_install_k8s(env, use_custom_yaml=use_custom_yaml)
        self.check_number_kube_nodes(env, k8sclient)
        self.check_running_containers(env)
        self.check_requirement_settings(env, use_custom_yaml=use_custom_yaml)
