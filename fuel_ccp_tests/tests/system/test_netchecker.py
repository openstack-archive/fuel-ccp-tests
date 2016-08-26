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

from base_test import SystemBaseTest
from devops.helpers.helpers import wait, wait_pass
from fuel_ccp_tests import logger
from fuel_ccp_tests.helpers import ext
from test_ccp_install_k8s import FuelCCPInstallerConfigMixin


LOG = logger.logger


class TestFuelCCPNetChecker(SystemBaseTest,
                            FuelCCPInstallerConfigMixin):
    """Test class for network connectivity verification in k8s"""

    @staticmethod
    def git_clone(underlay, host, repository, destination):
        underlay.sudo_check_call(
            'git clone {0} {1}'.format(repository, destination),
            node_name=host)

    @staticmethod
    def get_pods(underlay, namespace='default'):
        pod_status = underlay.sudo_check_call(
            "kubectl get --namespace={0} "
            "-o 'jsonpath={{.items[*].metadata.name}}' pods".format(namespace),
            node_name='master').stdout
        return ''.join(pod_status).split()

    @staticmethod
    def get_pod_status(underlay, podname):
        pod_status = underlay.sudo_check_call(
            "kubectl get "
            "-o 'jsonpath={{.status.phase}}' pod {0}".format(podname),
            node_name='master').stdout
        return ''.join(pod_status).lower()

    @staticmethod
    def get_ds_status(underlay, dsname):
        ds_current_num = underlay.sudo_check_call(
            "kubectl get -o 'jsonpath={{.status.currentNumberScheduled}}' "
            "ds {0}".format(dsname),
            node_name='master').stdout
        ds_desired_num = underlay.sudo_check_call(
            "kubectl get -o 'jsonpath={{.status.desiredNumberScheduled}}' "
            "ds {0}".format(dsname),
            node_name='master').stdout
        return int(''.join(ds_current_num)) == int(''.join(ds_desired_num))

    @staticmethod
    def wait_pod_running(underlay, podname, timeout=60, interval=5):
        wait(
            lambda: (TestFuelCCPNetChecker.get_pod_status(underlay, podname) ==
                     'running'), timeout=timeout, interval=interval)

    @staticmethod
    def wait_pod_deleted(underlay, podname, timeout=60, interval=5):
        wait(
            lambda: podname not in TestFuelCCPNetChecker.get_pods(underlay),
            timeout=timeout, interval=interval)

    @staticmethod
    def wait_ds_running(underlay, dsname, timeout=60, interval=5):
        wait(
            lambda: TestFuelCCPNetChecker.get_ds_status(underlay, dsname),
            timeout=timeout, interval=interval)

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

    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    def test_k8s_netchecker_calico(self, underlay, k8scluster, k8s_actions):
        """Test for deploying an k8s environment with Calico and check
           connectivity between its networks

        Scenario:
            1. Install k8s.
            2. Create docker registry service
            3. Go to kubernetes master node via SSH and clone
               network-checker-server code from GIT repository
            4. Build docker image with netchecker-server
            5. Pull the image with netchecker-server to the registry
            6. Go to kubernetes master node via SSH and clone
               network-checker-agent code from GIT repository
            7. Build docker image with netchecker-agent
            8. Pull the image with netchecker-agent to the registry
            9. Run netchecker-server service
            10. Run netchecker-agent replication cluster
            11. Get network verification status. Check status is 'OK'
            12. Randomly choose some slave, login to it via SSH, add blocking
                iptables rule
            13. Get network verification status, Check status is 'FAIL'
            14. Recover iptables state on the slave
            15. Get network verification status. Check status is 'OK'
        """

        # STEP #1
        # FIXME: use k8sclient instead of CLI for all actions with kubernetes
        # (currently it's impossible with revert from snapshot)
        # k8sclient = k8s_actions.get_k8sclient()

        # STEP #2
        k8scluster.create_registry(node_name='master')

        # STEP #3
        self.git_clone(
            underlay,
            'master',
            'https://review.fuel-infra.org/nextgen/mcp-netchecker-server',
            '/tmp/mcp-netchecker-server'
        )

        # STEP #4
        underlay.sudo_check_call(
            'cd /tmp/mcp-netchecker-server/ && '
            'docker build -t 127.0.0.1:31500/netchecker/server:latest .',
            node_name='master')

        # STEP #5
        underlay.sudo_check_call(
            'docker push 127.0.0.1:31500/netchecker/server:latest',
            node_name='master')

        # STEP #6
        self.git_clone(
            underlay,
            'master',
            'https://review.fuel-infra.org/nextgen/mcp-netchecker-agent',
            '/tmp/mcp-netchecker-agent'
        )

        # STEP #7
        underlay.sudo_check_call(
            'cd /tmp/mcp-netchecker-agent/docker && '
            'docker build -t 127.0.0.1:31500/netchecker/agent:latest .',
            node_name='master')

        # STEP #8
        underlay.sudo_check_call(
            'docker push 127.0.0.1:31500/netchecker/agent:latest',
            node_name='master')

        # STEP #9
        underlay.sudo_check_call(
            'cd /tmp/mcp-netchecker-server/ && '
            'kubectl create -f k8s_resources/netchecker-server_pod.yaml',
            node_name='master')
        underlay.sudo_check_call(
            'cd /tmp/mcp-netchecker-server/ && '
            'kubectl create -f k8s_resources/netchecker-server_svc.yaml',
            node_name='master')
        self.wait_pod_running(underlay, 'netchecker-server')

        # STEP #10
        underlay.sudo_check_call(
            "kubectl get nodes | awk '/Ready/{print $1}' | "
            "xargs -I {} kubectl label nodes {} netchecker=agent",
            node_name='master')
        underlay.sudo_check_call(
            'cd /tmp/mcp-netchecker-agent/ && '
            'kubectl create -f netchecker-agent.yaml',
            node_name='master')
        self.wait_ds_running(underlay, dsname='netchecker-agent')
        self.wait_ds_running(underlay, dsname='netchecker-agent-hostnet')

        # STEP #11
        # currently agents need some time to start reporting to the server
        time.sleep(120)
        self.check_network(underlay, works=True)

        # STEP #12
        slave_nodes = [n for n in underlay.node_names() if n != 'master']
        random.shuffle(slave_nodes)
        target_slave = slave_nodes.pop()

        # stop netchecker-server
        underlay.sudo_check_call(
            'kubectl delete pod/netchecker-server',
            node_name='master')
        self.wait_pod_deleted(underlay, 'netchecker-server')

        # block forward traffic (from containers w\o host-net)
        # to netchecker-server on the slave node
        underlay.sudo_check_call(
            'iptables -A FORWARD -p tcp --dport 8081 -j DROP',
            node_name=target_slave)

        # start netchecker-server
        underlay.sudo_check_call(
            'cd /tmp/mcp-netchecker-server/ && '
            'kubectl create -f k8s_resources/netchecker-server_pod.yaml',
            node_name='master')
        self.wait_pod_running(underlay, 'netchecker-server')
        self.wait_netchecker_running(underlay, timeout=120)

        # STEP #13
        # currently agents need some time to start reporting to the server
        time.sleep(120)
        self.check_network(underlay, works=False)

        # STEP #14
        # remove blocking firewall rule
        underlay.sudo_check_call(
            'iptables -D FORWARD -p tcp --dport 8081 -j DROP',
            node_name=target_slave)

        # STEP #15
        # currently agents need some time to start reporting to the server
        time.sleep(240)
        self.check_network(underlay, works=True)
