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
import requests
import yaml

from devops.helpers import helpers
from k8sclient.client import rest

import base_test
from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests.helpers import utils
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

    def start_netchecker_server(self, k8s):
        with open(self.pod_yaml_file) as pod_conf:
            for pod_spec in yaml.load_all(pod_conf):
                for container in pod_spec['spec']['containers']:
                    if container['name'] == 'netchecker-server':
                        container['image'] = '{0}:{1}'.format(
                            settings.MCP_NETCHECKER_SERVER_IMAGE_REPO,
                            settings.MCP_NETCHECKER_SERVER_VERSION)
                try:
                    if k8s.api.pods.get(name=pod_spec['metadata']['name']):
                        LOG.debug('Network checker server pod {} is '
                                  'already running! Skipping resource creation'
                                  '.'.format(pod_spec['metadata']['name']))
                        continue
                except rest.ApiException as e:
                    if e.status == 404:
                        k8s.check_pod_create(body=pod_spec)
                    else:
                        raise e

        with open(self.svc_yaml_file) as svc_conf:
            for svc_spec in yaml.load_all(svc_conf):
                try:
                    if k8s.api.services.get(
                            name=svc_spec['metadata']['name']):
                        LOG.debug('Network checker server service {} is '
                                  'already running! Skipping resource creation'
                                  '.'.format(svc_spec['metadata']['name']))
                        continue
                except rest.ApiException as e:
                    if e.status == 404:
                        k8s.check_service_create(body=svc_spec)
                    else:
                        raise e

    def start_netchecker_agent(self, underlay, k8s):
        # TODO(apanchenko): use python API client here when it will have
        # TODO(apanchenko): needed functionality (able work with labels)
        underlay.sudo_check_call(
            "kubectl get nodes | awk '/Ready/{print $1}' | "
            "xargs -I {} kubectl label nodes {} netchecker=agent --overwrite",
            node_name='master')

        with open(self.ds_yaml_file) as ds_conf:
            for daemon_set_spec in yaml.load_all(ds_conf):
                for container in (daemon_set_spec['spec']['template']['spec']
                                  ['containers']):
                    if container['name'] == 'netchecker-agent':
                        container['image'] = '{0}:{1}'.format(
                            settings.MCP_NETCHECKER_AGENT_IMAGE_REPO,
                            settings.MCP_NETCHECKER_AGENT_VERSION)
                k8s.check_ds_create(body=daemon_set_spec)
                k8s.wait_ds_ready(dsname=daemon_set_spec['metadata']['name'])

    @staticmethod
    @utils.retry(3, requests.exceptions.RequestException)
    def get_netchecker_status(kube_host_ip, netchecker_pod_port=31081):
        net_status_url = 'http://{0}:{1}/api/v1/connectivity_check'.format(
            kube_host_ip, netchecker_pod_port)
        return requests.get(net_status_url, timeout=5)

    @staticmethod
    def wait_netchecker_running(kube_host_ip, timeout=120, interval=5):
        helpers.wait_pass(
            lambda: TestFuelCCPNetChecker.get_netchecker_status(kube_host_ip),
            timeout=timeout, interval=interval)

    def check_network(self, kube_host_ip, works=True):
        if works:
            assert self.get_netchecker_status(kube_host_ip).status_code == 204
        else:
            assert self.get_netchecker_status(kube_host_ip).status_code == 400

    def wait_check_network(self, kube_host_ip, works=True, timeout=120,
                           interval=5):
        helpers.wait_pass(
            lambda: self.check_network(kube_host_ip, works=works),
            timeout=timeout, interval=interval)

    @staticmethod
    def calico_block_traffic_on_node(underlay, target_node):
        LOG.info('Blocked traffic to the network checker service from '
                 'containers on node "{}".'.format(target_node))
        underlay.sudo_check_call(
            'calicoctl profile calico-k8s-network rule add '
            '--at=1 outbound deny tcp to ports 8081',
            node_name=target_node)

    @staticmethod
    def calico_unblock_traffic_on_node(underlay, target_node):
        LOG.info('Unblocked traffic to the network checker service from '
                 'containers on node "{}".'.format(target_node))
        underlay.sudo_check_call(
            'calicoctl profile calico-k8s-network rule remove outbound --at=1',
            node_name=target_node)


@pytest.mark.usefixtures("check_netchecker_files")
@pytest.mark.usefixtures("check_netchecker_images_settings")
class TestFuelCCPNetChecker(base_test.SystemBaseTest,
                            TestFuelCCPNetCheckerMixin):
    """Test class for network connectivity verification in k8s"""

    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    def test_k8s_netchecker(self, underlay, k8scluster, config,
                            show_step):
        """Test for deploying an k8s environment with Calico and check
           connectivity between its networks

        Scenario:
            1. Install k8s.
            2. Run netchecker-server service
            3. Run netchecker-agent daemon set
            4. Get network verification status. Check status is 'OK'
            5. Randomly choose some k8s node, login to it via SSH, add blocking
               rule to the calico policy. Restart network checker server
            6. Get network verification status, Check status is 'FAIL'
            7. Recover calico profile state on the node
            8. Get network verification status. Check status is 'OK'

        Duration: 300 seconds
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

        # STEP #5
        show_step(5)
        target_node = underlay.get_random_node()
        self.calico_block_traffic_on_node(underlay, target_node)

        # STEP #6
        show_step(6)
        self.wait_check_network(config.k8s.kube_host, works=False)

        # STEP #7
        show_step(7)
        self.calico_unblock_traffic_on_node(underlay, target_node)

        # STEP #8
        show_step(8)
        self.wait_check_network(config.k8s.kube_host, works=True)
