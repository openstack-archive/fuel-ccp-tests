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
from fuel_ccp_tests.helpers import ext


@pytest.mark.fuel_ccp_scale_k8s
@pytest.mark.system_lcm
class TestLCMScaleK8s(base_test.SystemBaseTest):
    """Test class for testing k8s scale by fuel-ccp-installer

       pytest.mark: fuel_ccp_scale_k8s
    """

    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    def test_lcm_k8s_scale_up(self, hardware, underlay, k8scluster):
        """Test for scale an k8s environment

        pytest.mark: k8s_installed_default

        Require:
         - already installed k8s cluster with node roles 'k8s'
         - fuel-devops environment with additional node roles 'k8s_scale'

        Scenario:
            1. Check number of kube nodes match underlay nodes.
            2. Check etcd health.
            3. Add to 'underlay' new nodes for k8s scale
            4. Run fuel-ccp installer for old+new k8s nodes
            5. Check number of kube nodes match underlay nodes.
            6. Check etcd health.
        """
        k8sclient = k8scluster.api

        self.check_number_kube_nodes(underlay, k8sclient)
        self.check_etcd_health(underlay)

        config_ssh_scale = hardware.get_ssh_data(
            roles=[ext.NODE_ROLE.k8s_scale])
        underlay.add_config_ssh(config_ssh_scale)

        k8scluster.install_k8s()

        self.check_number_kube_nodes(underlay, k8sclient)
        self.check_etcd_health(underlay)
