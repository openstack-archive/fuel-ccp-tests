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

import os
import pytest
import yaml

import base_test
from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests.helpers import netchecker
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings

LOG = logger.logger


class TestFuelCCPNetCheckerMixin:
    pod_yaml_file = os.path.join(
        settings.NETCHECKER_SERVER_DIR,
        'k8s_resources/netchecker-server_pod.yaml')
    svc_yaml_file = os.path.join(
        settings.NETCHECKER_SERVER_DIR,
        'k8s_resources/netchecker-server_svc.yaml')
    ds_yaml_file = os.path.join(
        settings.NETCHECKER_AGENT_DIR, 'netchecker-agent.yaml')
    netchecker_files = (pod_yaml_file, svc_yaml_file, ds_yaml_file)

    @property
    def pod_spec(self):
        if not os.path.isfile(self.pod_yaml_file):
           return None
        with open(self.pod_yaml_file) as pod_conf:
            return yaml.load(pod_conf)

    @property
    def svc_spec(self):
        if not os.path.isfile(self.svc_yaml_file):
            return None
        with open(self.svc_yaml_file) as svc_conf:
            return yaml.load(svc_conf)

    @property
    def ds_spec(self):
        if not os.path.isfile(self.ds_yaml_file):
            return None
        with open(self.ds_yaml_file) as ds_conf:
            return [i for i in yaml.load_all(ds_conf)]


@pytest.mark.usefixtures("check_netchecker_files")
@pytest.mark.usefixtures("check_netchecker_images_settings")
class TestFuelCCPNetChecker(base_test.SystemBaseTest,
                            TestFuelCCPNetCheckerMixin):
    """Test class for network connectivity verification in k8s"""

    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    def test_k8s_netchecker(self, underlay, k8scluster, config, show_step):
        """Test for deploying an k8s environment with Calico and check
           connectivity between its networks

        Scenario:
            1. Install k8s.
            2. Run netchecker-server service
            3. Check that netchecker-server returns 400: 'There are no pods'
            4. Run netchecker-agent daemon set
            5. Get network verification status. Check status is 'OK'
            6. Randomly choose some k8s node, login to it via SSH, add blocking
               rule to the calico policy. Restart network checker server
            7. Get network verification status, Check status is 'FAIL'
            8. Recover calico profile state on the node
            9. Get network verification status. Check status is 'OK'

        Duration: 300 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8scluster.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        netchecker.start_server(k8s=k8scluster, pod_spec=self.pod_spec,
                                svc_spec=self.svc_spec)
        netchecker.wait_running(config.k8s.kube_host, timeout=240)

        # STEP #3
        show_step(3)
        netchecker.wait_check_network(config.k8s.kube_host, works=False)

        # STEP #4
        show_step(4)
        netchecker.start_agent(k8s=k8scluster, ds_spec=self.ds_spec)

        # STEP #5
        show_step(5)
        netchecker.wait_check_network(config.k8s.kube_host, works=True)

        # STEP #6
        show_step(6)
        target_node = underlay.get_random_node()
        netchecker.calico_block_traffic_on_node(underlay, target_node)

        # STEP #7
        show_step(7)
        netchecker.wait_check_network(config.k8s.kube_host, works=False)

        # STEP #8
        show_step(8)
        netchecker.calico_unblock_traffic_on_node(underlay, target_node)

        # STEP #9
        show_step(9)
        netchecker.wait_check_network(config.k8s.kube_host, works=True)
