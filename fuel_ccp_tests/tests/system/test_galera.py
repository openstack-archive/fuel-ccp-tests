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
from devops.helpers import helpers

import base_test
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import post_os_deploy_checks
from fuel_ccp_tests.helpers import mysql
from fuel_ccp_tests.helpers import utils

LOG = logger.logger


class TestGalera(base_test.SystemBaseTest):
    """ Galera scale and destructive scenarios

    """
    namespace = settings.CCP_CONF['kubernetes']['namespace']

    def get_pods(self, k8s):
        return \
            k8s.get_running_pods('galera', self.namespace)

    def check_replication(self, remote, pods):
        any_pod_name = pods[0].name
        db_name = 'test_db_{}'.format(utils.rand_number())
        table_name = 'test_table_{}'.format(utils.rand_number())
        value = utils.rand_number()
        mysql.populate_data(remote, any_pod_name, self.namespace, db_name, table_name, value)
        for pod in pods:
            mysql.check_data(remote, pod.name, self.namespace, db_name, table_name, value)

    @pytest.mark.fail_snapshot
    @pytest.mark.galera_kill_pod
    @pytest.mark.galera
    def test_galera_kill_pod(self, hardware, underlay, config,
                                  ccpcluster, k8s_actions, show_step,
                                  galera_deployed):
        """Kill galera pod

        Scenario:
        1. Revert snapshot with deployed galera
        2. Kill one galera pode
        3. Check pod was recreated and joined cluster
        4. Check galera replication
        5. Create 2 vms

        Duration 30 min
        """
        show_step(2)        
        galera_pods = self.get_pods(k8s_actions)
        LOG.info("pods before kill are {}".format(galera_pods))
        k8s_actions.check_pod_delete(
            galera_pods[0],
            namespace=self.namespace)
        show_step(3)
        helpers.wait(lambda: (len(self.get_pods(k8s_actions)) ==
                              len(galera_pods)),
                     timeout=600,
                     timeout_msg="Galera pod wasn't scheduled after kill")

        helpers.wait(lambda: ccpcluster.status() == 'ok',
                     timeout=600,
                     timeout_msg="Cluster status is not ok, status"
                                 " is {}".format(ccpcluster.status()))

        remote = underlay.remote(host=config.k8s.kube_host)
        show_step(4)
        galera_pods_after_kill = self.get_pods(k8s_actions)
        self.check_replication(remote, galera_pods_after_kill)
        show_step(5)
        remote.check_call(
            "source openrc-{0}; bash fuel-ccp/tools/deploy-test-vms.sh -k {0}"
            " -a create".format(self.namespace), timeout=600)

    @pytest.mark.fail_snapshot
    @pytest.mark.galera_shutdown
    @pytest.mark.galera
    def test_galera_shutdown_node(self, hardware, underlay, config,
                                  ccpcluster, k8s_actions, show_step,
                                  galera_deployed):
        """Shutdown galera node

        Scenario:
        1. Revert snapshot with deployed galera
        2. Shutdown one galera node
        3. Check galera state
        4. Check galera replication
        5. Create 2 vms

        Duration 30 min
        """
        show_step(2)
        galera_pods = self.get_pods(k8s_actions)
        galera_node = underlay.node_names()[1]
        galera_node_ip = underlay.host_by_node_name(galera_node)
        hardware.shutdown_node_by_ip(galera_node_ip)
        show_step(3)
        helpers.wait(lambda: (set(self.get_pods(k8s_actions)) -
                              set(galera_pods)),
                     timeout=600,
                     timeout_msg="Galera pod wasn't terminated after node shutdown")

        helpers.wait(lambda: ccpcluster.status() == 'ok',
                     timeout=600,
                     timeout_msg="Cluster status is not ok, status"
                                 " is {}".format(ccpcluster.status()))
        
        remote = underlay.remote(host=config.k8s.kube_host)
        show_step(4)
        galera_pods_after_kill = self.get_pods(k8s_actions)
        self.check_replication(remote, galera_pods_after_kill)
        show_step(5)
        remote.check_call(
            "source openrc-{0}; bash fuel-ccp/tools/deploy-test-vms.sh -k {0}"
            " -a create".format(
                settings.CCP_CONF["kubernetes"]["namespace"]),
            timeout=600)

    @pytest.mark.fail_snapshot
    @pytest.mark.galera_cold_restart
    @pytest.mark.galera
    def test_galera_cold_restart_node(self, hardware, underlay, config,
                                      ccpcluster, k8s_actions, show_step,
                                      galera_deployed):
        """Cold restart galera node

        Scenario:
        1. Revert snapshot with deployed galera
        2. Cold restart one galera node
        3. Check galera state
        4. Check galera replication
        5. Create 2 vms

        Duration 30 min
        """
        show_step(2)
        galera_pods = self.get_pods(k8s_actions)
        galera_node = underlay.node_names()[1]
        galera_node_ip = underlay.host_by_node_name(galera_node)
        hardware.shutdown_node_by_ip(galera_node_ip)
        hardware.start_node_by_ip(underlay.host_by_node_name('slave-0'))
        show_step(3)
        helpers.wait(lambda: (set(self.get_pods(k8s_actions)) -
                              set(galera_pods)),
                     timeout=600,
                     timeout_msg="Galera pod wasn't terminated after node restart")

        helpers.wait(lambda: ccpcluster.status() == 'ok',
                     timeout=600,
                     timeout_msg="Cluster status is not ok, status"
                                 " is {}".format(ccpcluster.status()))

        remote = underlay.remote(host=config.k8s.kube_host)
        show_step(4)
        galera_pods_after_kill = self.get_pods(k8s_actions)
        self.check_replication(remote, galera_pods_after_kill)
        
        show_step(5)
        remote.check_call(
            "source openrc-{0}; bash fuel-ccp/tools/deploy-test-vms.sh -k {0}"
            " -a create".format(
                settings.CCP_CONF["kubernetes"]["namespace"]),
            timeout=600)

    @pytest.mark.fail_snapshot
    @pytest.mark.galera_poweroff
    @pytest.mark.galera
    def test_galera_poweroff_node(self, hardware, underlay, config,
                                  ccpcluster, k8s_actions, show_step,
                                  galera_deployed):
        """Poweroff galera node

        Scenario:
        1. Revert snapshot with deployed galera
        2. Poweroff one galera node
        3. Check galera state
        4. Check galera replication
        5. Create 2 vms

        Duration 30 min
        """
        galera_pods = self.get_pods(k8s_actions)
        galera_node = underlay.node_names()[1]
        galera_node_ip = underlay.host_by_node_name(galera_node)
        show_step(2)
        underlay.sudo_check_call('shutdown +1', node_name=galera_node)
        hardware.shutdown_node_by_ip(galera_node_ip)
        hardware.wait_node_is_offline(galera_node_ip, 90)
        show_step(3)
        helpers.wait(lambda: (set(self.get_pods(k8s_actions)) -
                              set(galera_pods)),
                     timeout=600,
                     timeout_msg="Galera pod wasn't terminated after node poweroff")

        helpers.wait(lambda: ccpcluster.status() == 'ok',
                     timeout=600,
                     timeout_msg="Cluster status is not ok, status"
                                 " is {}".format(ccpcluster.status()))

        remote = underlay.remote(host=config.k8s.kube_host)
        show_step(4)
        galera_pods_after_kill = self.get_pods(k8s_actions)
        self.check_replication(remote, galera_pods_after_kill)
        
        show_step(5)
        remote.check_call(
            "source openrc-{0}; bash fuel-ccp/tools/deploy-test-vms.sh -k {0}"
            " -a create".format(
                settings.CCP_CONF["kubernetes"]["namespace"]),
            timeout=600)

    @pytest.mark.fail_snapshot
    @pytest.mark.galera_soft_reboot
    @pytest.mark.galera
    def test_galera_soft_reboot_node(self, hardware, underlay, config,
                                     ccpcluster, k8s_actions, show_step,
                                     galera_deployed):
        """Soft reboot galera node

        Scenario:
        1. Revert snapshot with deployed galera
        2. Soft reboot one galera node
        3. Check galera state
        4. Check galera replication
        5. Create 2 vms

        Duration 30 min
        """
        galera_pods = self.get_pods(k8s_actions)
        galera_node = underlay.node_names()[1]
        galera_node_ip = underlay.host_by_node_name(galera_node)
        show_step(2)
        underlay.sudo_check_call('shutdown +1', node_name=galera_node)
        hardware.shutdown_node_by_ip(galera_node_ip)
        hardware.wait_node_is_offline(galera_node_ip, 90)
        hardware.start_node_by_ip(galera_node_ip)
        hardware.wait_node_is_online(galera_node_ip, 180)
        show_step(3)
        helpers.wait(lambda: (set(self.get_pods(k8s_actions)) -
                              set(galera_pods)),
                     timeout=600,
                     timeout_msg="Galera pod wasn't terminated after node reboot")

        helpers.wait(lambda: ccpcluster.status() == 'ok',
                     timeout=600,
                     timeout_msg="Cluster status is not ok, status"
                                 " is {}".format(ccpcluster.status()))

        remote = underlay.remote(host=config.k8s.kube_host)
        show_step(4)
        galera_pods_after_kill = self.get_pods(k8s_actions)
        self.check_replication(remote, galera_pods_after_kill)
        show_step(5)
        remote.check_call(
            "source openrc-{0}; bash fuel-ccp/tools/deploy-test-vms.sh -k {0}"
            " -a create".format(
                settings.CCP_CONF["kubernetes"]["namespace"]),
            timeout=600)

    @pytest.mark.fail_snapshot
    @pytest.mark.galera_cluster_shutdown
    @pytest.mark.galera
    def test_galera_cluster_shutdown(self, hardware, underlay, config,
                                     ccpcluster, k8s_actions, show_step,
                                     galera_deployed):
        """Galera cluster shutdown

        Scenario:
        1. Revert snapshot with deployed galera
        2. Shutdown all galera nodes and start them one by one
        3. Check galera state
        4. Check galera replication
        5. Create 2 vms

        Duration 30 min
        """
        galera_pods = self.get_pods(k8s_actions)
        galera_nodes = underlay.node_names()[:3]
        galera_node_ips = []
        show_step(2)
        for galera_node in galera_nodes:
            galera_node_ip = underlay.host_by_node_name(galera_node)
            galera_node_ips.append(galera_node_ip)
            hardware.shutdown_node_by_ip(galera_node_ip)
            hardware.wait_node_is_offline(galera_node_ip, 90)
        for galera_ip in galera_node_ips:
            hardware.start_node_by_ip(galera_ip)
            hardware.wait_node_is_online(galera_ip, 180)
        show_step(3)
        helpers.wait(lambda: (set(self.get_pods(k8s_actions)) -
                              set(galera_pods)),
                     timeout=600,
                     timeout_msg="Galera pods weren't terminated after cluster shutdown")

        helpers.wait(lambda: ccpcluster.status() == 'ok',
                     timeout=600,
                     timeout_msg="Cluster status is not ok, status"
                                 " is {}".format(ccpcluster.status()))

        remote = underlay.remote(host=config.k8s.kube_host)
        show_step(4)
        galera_pods_after_kill = self.get_pods(k8s_actions)
        self.check_replication(remote, galera_pods_after_kill)
        show_step(5)
        remote.check_call(
            "source openrc-{0}; bash fuel-ccp/tools/deploy-test-vms.sh -k {0}"
            " -a create".format(
                settings.CCP_CONF["kubernetes"]["namespace"]),
            timeout=600)

    @pytest.mark.fail_snapshot
    @pytest.mark.galera_scale_up_down
    @pytest.mark.galera
    def test_galera_scale(self, hardware, underlay, config,
                          ccpcluster, k8s_actions, show_step,
                          galera_deployed):
        """Galera cluster scale

        Scenario:
        1. Revert snapshot with deployed galera
        2. Scale up galera to 5 replicas
        3. Check galera state
        4. Check galera replication
        5. Check number of galera pods
        6. Create 2 vms
        7. Scale down galera to 3 replicas
        8. Check galera state
        9. Check galera replication
        10. Check number of galera pods
        11. Create 2 vms

        Duration 30 min
        """
        show_step(2)
        with underlay.yaml_editor('./config_1.yaml',
                                  host=config.k8s.kube_host) as editor:
            editor.content['replicas']['galera'] = 5
        with underlay.yaml_editor('/tmp/3galera_1comp.yaml',
                                  host=config.k8s.kube_host) as editor:
            del editor.content['nodes']['node[1-3]']
            editor.content['nodes']['node[1-5]'] = {'roles': ['galera']}

        ccpcluster.deploy(params={"config-file": "./config_1.yaml"},
                          use_cli_params=True)
        post_os_deploy_checks.check_jobs_status(k8s_actions.api, timeout=2000)
        post_os_deploy_checks.check_pods_status(k8s_actions.api)
        show_step(3)
        helpers.wait(lambda: ccpcluster.status() == 'ok',
                     timeout=600,
                     timeout_msg="Cluster status is not ok, status"
                                 " is {}".format(ccpcluster.status()))

        remote = underlay.remote(host=config.k8s.kube_host)
        show_step(4)
        galera_pods_after_scale = self.get_pods(k8s_actions)
        self.check_replication(remote, galera_pods_after_scale)
        
        show_step(5)
        
        assert len(galera_pods_after_scale) == 5,\
            "Expected to have 5 galera pods, got {}".format(galera_pods_after_scale)

        show_step(6)        
        remote.check_call(
            "source openrc-{0}; bash fuel-ccp/tools/deploy-test-vms.sh -k {0}"
            " -a create".format(
                settings.CCP_CONF["kubernetes"]["namespace"]),
            timeout=600)
        show_step(7)
        with underlay.yaml_editor('./config_1.yaml',
                                  host=config.k8s.kube_host) as editor:
            editor.content['replicas']['galera'] = 3
        with underlay.yaml_editor('/tmp/3galera_1comp.yaml',
                                  host=config.k8s.kube_host) as editor:
            del editor.content['nodes']['node[1-5]']
            editor.content['nodes']['node[1-3]'] = {'roles': ['galera']}

        ccpcluster.deploy(params={"config-file": "./config_1.yaml"},
                          use_cli_params=True)
        post_os_deploy_checks.check_jobs_status(k8s_actions.api, timeout=2000)
        post_os_deploy_checks.check_pods_status(k8s_actions.api)
        show_step(8)
        helpers.wait(lambda: ccpcluster.status() == 'ok',
                     timeout=600,
                     timeout_msg="Cluster status is not ok, status"
                                 " is {}".format(ccpcluster.status()))
        
        show_step(9)
        galera_pods_after_scale = self.get_pods(k8s_actions)
        self.check_replication(remote, galera_pods_after_scale)
        
        show_step(10)
        
        assert len(galera_pods_after_scale) == 3, ("Expected to have 3 galera pods, "
                                  "got {}".format(galera_pods_after_scale))
        show_step(11)
        remote.check_call(
            "source openrc-{0}; bash fuel-ccp/tools/deploy-test-vms.sh -k {0}"
            " -a create".format(
                settings.CCP_CONF["kubernetes"]["namespace"]),
            timeout=600)
