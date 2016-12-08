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

import time

import pytest

import base_test
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import netchecker

LOG = logger.logger


@pytest.mark.usefixtures("check_calico_images_settings")
class TestFuelCCPCalico(base_test.SystemBaseTest):
    """Test class for Calico network plugin in k8s"""

    kube_settings = settings.DEFAULT_CUSTOM_YAML
    kube_settings['deploy_netchecker'] = False

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
        netchecker.start_server(k8s=k8scluster)
        netchecker.wait_running(config.k8s.kube_host, timeout=240)

        # STEP #3
        show_step(3)
        netchecker.start_agent(k8s=k8scluster)

        # STEP #4
        show_step(4)
        netchecker.wait_check_network(config.k8s.kube_host, works=True)


@pytest.mark.usefixtures("check_calico_images_settings")
class TestFuelCCPCalicoPolicy(base_test.SystemBaseTest):
    """Test class for Calico network policies in k8s"""

    kube_settings = settings.DEFAULT_CUSTOM_YAML
    kube_settings['deploy_netchecker'] = False
    kube_settings['enable_network_policy'] = True

    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_k8s_netchecker_calico(self, k8scluster, config,
                                   show_step):
        """Test for deploying k8s environment with Calico plugin and check
           network connectivity between pods

        Scenario:
            1. Install k8s with Calico network plugin.
            2. Run netchecker-server service.
            3. Run netchecker-agent daemon set.
            4. Get network verification status. Check status is 'OK'.
            5. Repeat step #4 30 times within 30 minutes

        Duration: 3000 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8scluster.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        netchecker.start_server(k8s=k8scluster)
        netchecker.wait_running(config.k8s.kube_host, timeout=240)

        # STEP #3
        show_step(3)
        netchecker.start_agent(k8s=k8scluster)

        # STEP #4
        show_step(4)
        netchecker.wait_check_network(config.k8s.kube_host, works=True)

        show_step(5)
        for _ in range(0,30):
            time.sleep(60)
            netchecker.wait_check_network(config.k8s.kube_host, works=True)
