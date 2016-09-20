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
import test_netchecker

from fuel_ccp_tests import logger

LOG = logger.logger


@pytest.mark.usefixtures("check_netchecker_files")
@pytest.mark.usefixtures("check_netchecker_images_settings")
@pytest.mark.usefixtures("check_calico_images_settings")
@pytest.mark.component
class TestFuelCCPCalico(base_test.SystemBaseTest,
                        test_netchecker.TestFuelCCPNetCheckerMixin):
    """Test class for Calico network plugin in k8s"""

    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_k8s_netchecker_calico(self, underlay, k8scluster, config,
                                   show_step):
        """Test for deploying k8s environment with Calico plugin and check
           network connectivity between pods

        Scenario:
            1. Install k8s with Calico network plugin.
            2. Run netchecker-server service.
            3. Run netchecker-agent daemon set.
            4. Get network verification status. Check status is 'OK'.

        Duration: 3000 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8scluster.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        self.start_netchecker_server(k8s=k8scluster)
        self.wait_netchecker_running(config.k8s.kube_host, timeout=240)

        # STEP #3
        show_step(3)
        self.start_netchecker_agent(underlay, k8scluster)

        # STEP #4
        show_step(4)
        self.wait_check_network(config.k8s.kube_host, works=True)
