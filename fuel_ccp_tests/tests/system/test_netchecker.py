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

import json
import pytest
import random
import time
import os
import yaml

from devops.helpers.helpers import wait, wait_pass
from k8sclient.client.rest import ApiException

from base_test import SystemBaseTest
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import ext

LOG = logger.logger


class TestFuelCCPNetChecker(SystemBaseTest):
    """Test class for network connectivity verification in k8s"""

    @staticmethod
    def dir_upload(underlay, host, source, destination):
        with underlay.remote(node_name=host) as remote:
            remote.upload(source, destination)

    @staticmethod
    def get_ds_status(k8sclient, dsname):
        ds = k8sclient.daemonsets.get(name=dsname)
        return (ds.status.current_number_scheduled ==
                ds.status.desired_number_scheduled)

    @staticmethod
    def wait_ds_running(k8sclient, dsname, timeout=60, interval=5):
        wait(
            lambda: TestFuelCCPNetChecker.get_ds_status(k8sclient, dsname),
            timeout=timeout, interval=interval)

    @staticmethod
    def build_netchecker(underlay, stype, source_dir):
        if stype == 'agent':
            source_dir = '/'.join((source_dir, 'docker'))
        underlay.sudo_check_call(
            'cd {0} && docker build -t 127.0.0.1:31500/netchecker/'
            '{1}:latest .'.format(source_dir, stype),
            node_name='master')

    @staticmethod
    def push_netchecker(underlay, stype, registry='127.0.0.1:31500'):
        underlay.sudo_check_call(
            'docker push {0}/netchecker/{1}:latest'.format(registry, stype),
            node_name='master')

    def start_netchecker_server(self, k8sclient):
        pod_yaml_file = os.path.join(
            settings.NETCHECKER_SERVER_DIR,
            'k8s_resources/netchecker-server_pod.yaml')

        with open(pod_yaml_file) as pod_conf:
            for pod_spec in yaml.load_all(pod_conf):
                try:
                    if k8sclient.pods.get(name=pod_spec['metadata']['name']):
                        LOG.debug('Network checker server pod {} is '
                                  'already running! Skipping resource creation'
                                  '.'.format(pod_spec['metadata']['name']))
                        continue
                except ApiException as e:
                    if e.status == 404:
                        self.check_pod_create(body=pod_spec,
                                              k8sclient=k8sclient)
                    else:
                        raise e

        svc_yaml_file = os.path.join(
            settings.NETCHECKER_SERVER_DIR,
            'k8s_resources/netchecker-server_svc.yaml')

        with open(svc_yaml_file) as svc_conf:
            for svc_spec in yaml.load_all(svc_conf):
                try:
                    if k8sclient.services.get(
                            name=svc_spec['metadata']['name']):
                        LOG.debug('Network checker server pod {} is '
                                  'already running! Skipping resource creation'
                                  '.'.format(svc_spec['metadata']['name']))
                        continue
                except ApiException as e:
                    if e.status == 404:
                        self.check_service_create(body=svc_spec,
                                                  k8sclient=k8sclient)
                    else:
                        raise e

    def start_netchecker_agent(self, underlay, k8sclient):
        # TODO(apanchenko): use python API client here when it will have
        # TODO(apanchenko): needed functionality (able work with labels)
        underlay.sudo_check_call(
            "kubectl get nodes | awk '/Ready/{print $1}' | "
            "xargs -I {} kubectl label nodes {} netchecker=agent --overwrite",
            node_name='master')

        ds_yaml_file = os.path.join(
            settings.NETCHECKER_AGENT_DIR, 'netchecker-agent.yaml')

        with open(ds_yaml_file) as ds_conf:
            for daemon_set_spec in yaml.load_all(ds_conf):
                self.check_ds_create(body=daemon_set_spec,
                                     k8sclient=k8sclient)
                self.wait_ds_running(
                    k8sclient,
                    dsname=daemon_set_spec['metadata']['name'])

    @staticmethod
    def get_netchecker_status(underlay):
        raw_status = underlay.sudo_check_call(
            'curl -m 5 -s localhost:31081/api/v1/agents/',
            node_name='master').stdout
        return json.loads(''.join(raw_status))

    @staticmethod
    def wait_netchecker_running(underlay, timeout=60, interval=5):
        wait_pass(
            lambda: TestFuelCCPNetChecker.get_netchecker_status(underlay),
            timeout=timeout, interval=interval)

    @staticmethod
    def get_netchecker_pods(underlay):
        raw_num_pods = underlay.sudo_check_call(
            'kubectl get pods | grep -c netchecker-agent',
            node_name='master').stdout
        return int(''.join(raw_num_pods))

    def check_network(self, underlay, works=True):
        assert (self.get_netchecker_pods(underlay) ==
                len(self.get_netchecker_status(underlay))) == works

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
            'iptables -A FORWARD -p tcp --dport 8081 -j DROP',
            node_name=slave_node)

    @staticmethod
    def unblock_traffic_on_slave(underlay, slave_node):
        LOG.info('Unblocked traffic to the network checker service from '
                 'containers on node "{}".'.format(slave_node))
        underlay.sudo_check_call(
            'iptables -D FORWARD -p tcp --dport 8081 -j DROP',
            node_name=slave_node)

    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    def test_k8s_netchecker_calico(self, underlay, k8scluster, log_helper):
        """Test for deploying an k8s environment with Calico and check
           connectivity between its networks

        Scenario:
            1. Install k8s.
            2. Create docker registry service
            3. Upload local copy of the 'mcp-netchecker-server' repository
               to the kubernetes master node via SSH(SFTP)
            4. Build docker image with netchecker-server
            5. Push the image with netchecker-server to the registry
            6. Go to kubernetes master node via SSH and upload local copy of
               the 'mcp-netchecker-agent' repository to the remote directory
            7. Build docker image with netchecker-agent
            8. Push the image with netchecker-agent to the registry
            9. Run netchecker-server service
            10. Run netchecker-agent replication cluster
            11. Get network verification status. Check status is 'OK'
            12. Randomly choose some slave, login to it via SSH, add blocking
                iptables rule. Restart network checker server
            13. Get network verification status, Check status is 'FAIL'
            14. Recover iptables state on the slave
            15. Get network verification status. Check status is 'OK'

        Duration: 600 seconds
        """

        # STEP #1
        log_helper.show_step(1)
        k8sclient = k8scluster.api

        # STEP #2
        log_helper.show_step(2)
        k8scluster.create_registry()

        # STEP #3
        log_helper.show_step(3)
        self.dir_upload(underlay,
                        host='master',
                        source=settings.NETCHECKER_SERVER_DIR,
                        destination='/tmp/mcp-netchecker-server')

        # STEP #4
        log_helper.show_step(4)
        self.build_netchecker(underlay,
                              stype='server',
                              source_dir='/tmp/mcp-netchecker-server')

        # STEP #5
        log_helper.show_step(5)
        self.push_netchecker(underlay, stype='server')

        # STEP #6
        log_helper.show_step(6)
        self.dir_upload(underlay,
                        host='master',
                        source=settings.NETCHECKER_AGENT_DIR,
                        destination='/tmp/mcp-netchecker-agent')

        # STEP #7
        log_helper.show_step(7)
        self.build_netchecker(underlay,
                              stype='agent',
                              source_dir='/tmp/mcp-netchecker-agent')

        # STEP #8
        log_helper.show_step(8)
        self.push_netchecker(underlay, stype='agent')

        # STEP #9
        log_helper.show_step(9)
        self.start_netchecker_server(k8sclient=k8sclient)
        self.wait_netchecker_running(underlay, timeout=240)

        # STEP #10
        log_helper.show_step(10)
        self.start_netchecker_agent(underlay, k8sclient)

        # STEP #11
        # currently agents need some time to start reporting to the server
        log_helper.show_step(11)
        time.sleep(120)
        self.check_network(underlay, works=True)

        # STEP #12
        log_helper.show_step(12)
        target_slave = self.get_random_slave(underlay)

        # stop netchecker-server
        # FIXME(apanchenko): uncomment and remove deletion via CLI below
        # currently it fails due to labels:
        # AttributeError: 'object' object has no attribute 'swagger_types'
        # need a new version of k8sclient released with the following patch
        # https://review.openstack.org/#/c/366908/
        # self.check_pod_delete(
        #     k8s_pod=k8sclient.pods.get(name='netchecker-server'),
        #     k8sclient=k8sclient)
        underlay.sudo_check_call(
            'kubectl delete pod/netchecker-server',
            node_name='master')
        self.wait_pod_deleted(k8sclient, 'netchecker-server')

        self.block_traffic_on_slave(underlay, target_slave)

        # start netchecker-server
        self.start_netchecker_server(k8sclient=k8sclient)
        self.wait_netchecker_running(underlay, timeout=240)

        # STEP #13
        log_helper.show_step(13)
        # currently agents need some time to start reporting to the server
        time.sleep(120)
        self.check_network(underlay, works=False)

        # STEP #14
        log_helper.show_step(14)
        self.unblock_traffic_on_slave(underlay, target_slave)

        # STEP #15
        log_helper.show_step(15)
        # currently agents need some time to start reporting to the server
        time.sleep(240)
        self.check_network(underlay, works=True)
