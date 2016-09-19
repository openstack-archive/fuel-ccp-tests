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
import random
import requests
import yaml

from devops.helpers import helpers
from k8sclient.client import rest

import base_test
from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings

LOG = logger.logger


@pytest.fixture(scope='class')
def check_netchecker_files(request):
    files_missing = []
    for arg in request.cls.netchecker_files:
        if not os.path.isfile(arg):
            files_missing.append(arg)
    assert len(files_missing) == 0, \
        ("The following netchecker files not found: "
         "{0}!".format(', '.join(files_missing)))


@pytest.fixture(scope='class')
def check_netchecker_images():
    settings_missing = []
    for setting in ('MCP_NETCHECKER_AGENT_IMAGE_REPO',
                    'MCP_NETCHECKER_AGENT_VERSION',
                    'MCP_NETCHECKER_SERVER_IMAGE_REPO',
                    'MCP_NETCHECKER_SERVER_VERSION'):
        if not getattr(settings, setting, None):
            settings_missing.append(setting)
    assert len(settings_missing) == 0, \
        ("The following environment variables are not set: "
         "{0}!".format(', '.join(settings_missing)))


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


@pytest.mark.usefixtures("check_netchecker_files")
@pytest.mark.usefixtures("check_netchecker_images")
@pytest.mark.system
class TestFuelCCPNetChecker(base_test.SystemBaseTest,
                            TestFuelCCPNetCheckerMixin):
    """Test class for network connectivity verification in k8s"""

    @staticmethod
    def dir_upload(underlay, host, source, destination):
        with underlay.remote(node_name=host) as remote:
            remote.upload(source, destination)

    @staticmethod
    def get_ds_status(k8s, dsname):
        ds = k8s.api.daemonsets.get(name=dsname)
        return (ds.status.current_number_scheduled ==
                ds.status.desired_number_scheduled)

    @staticmethod
    def wait_ds_running(k8s, dsname, timeout=60, interval=5):
        helpers.wait(
            lambda: TestFuelCCPNetChecker.get_ds_status(k8s, dsname),
            timeout=timeout, interval=interval)

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
                TestFuelCCPNetChecker.wait_ds_running(
                    k8s,
                    dsname=daemon_set_spec['metadata']['name'])

    @staticmethod
    def get_netchecker_status(kube_host_ip, netchecker_pod_port=31081):
        net_status_url = 'http://{0}:{1}/api/v1/connectivity_check'.format(
            kube_host_ip, netchecker_pod_port)
        return requests.get(net_status_url)

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
    def get_random_slave(underlay):
        slave_nodes = [n for n in underlay.node_names() if n != 'master']
        if not slave_nodes:
            return None
        random.shuffle(slave_nodes)
        return slave_nodes.pop()

    @staticmethod
    def block_traffic_on_slave(underlay, slave_node):
        LOG.info('Blocked traffic to the network checker service from '
                 'containers on node "{}".'.format(slave_node))
        underlay.sudo_check_call(
            'calicoctl profile calico-k8s-network rule add '
            '--at=1 outbound deny tcp to ports 8081',
            node_name=slave_node)

    @staticmethod
    def unblock_traffic_on_slave(underlay, slave_node):
        LOG.info('Unblocked traffic to the network checker service from '
                 'containers on node "{}".'.format(slave_node))
        underlay.sudo_check_call(
            'calicoctl profile calico-k8s-network rule remove outbound --at=1',
            node_name=slave_node)

    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    def test_k8s_netchecker_calico(self, underlay, k8scluster, config,
                                   show_step):
        """Test for deploying an k8s environment with Calico and check
           connectivity between its networks

        Scenario:
            1. Install k8s.
            2. Run netchecker-server service
            3. Run netchecker-agent daemon set
            4. Get network verification status. Check status is 'OK'
            5. Randomly choose some slave, login to it via SSH, add blocking
               rule to the calico policy. Restart network checker server
            6. Get network verification status, Check status is 'FAIL'
            7. Recover calico profile state on the slave
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
        # currently agents need some time to start reporting to the server
        show_step(4)
        self.wait_check_network(config.k8s.kube_host, works=True)

        # STEP #5
        show_step(5)
        target_slave = self.get_random_slave(underlay)
        self.block_traffic_on_slave(underlay, target_slave)

        # STEP #6
        show_step(6)
        self.wait_check_network(config.k8s.kube_host, works=False)

        # STEP #7
        show_step(7)
        self.unblock_traffic_on_slave(underlay, target_slave)

        # STEP #8
        show_step(8)
        self.wait_check_network(config.k8s.kube_host, works=True)
