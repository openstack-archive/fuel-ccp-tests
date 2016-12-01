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
from copy import deepcopy
import os
import pytest

import base_test
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests.helpers import post_os_deploy_checks

LOG = logger.logger


class TestGalera(base_test.SystemBaseTest):
    """Deploy OpenStack cluster with enabled Galera

    """
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
    @pytest.mark.fail_snapshot
    @pytest.mark.galera
    @pytest.mark.galera_deploy
    @pytest.mark.snapshot_needed(name="galera_cluster")
    def test_deploy_galera(self, underlay, config, ccpcluster, k8s_actions,
                           show_step):
        """Deploy base environment

        Scenario:
        1. Build images if external registry is not provided
        2. Upload topology with galera
        3. Deploy OS cluster
        4. Check deployment
        5. Check galera state
        6. Create 2 vms

        Duration 90 min
        """
        general_config = deepcopy(settings.CCP_CONF)
        general_config['replicas'] = {'galera': 3}
        show_step(1)
        if settings.BUILD_IMAGES:
            k8s_actions.create_registry()
            ccpcluster.build()
        topology_path = \
            os.getcwd() + '/fuel_ccp_tests/templates/k8s_templates/' \
                          '3galera_1comp.yaml'
        remote = underlay.remote(host=config.k8s.kube_host)
        show_step(2)
        remote.upload(topology_path, '/tmp')
        ccpcluster.put_yaml_config('./config_1.yaml', general_config)
        ccpcluster.add_includes('./config_1.yaml', [
            settings.CCP_DEPLOY_CONFIG,
            settings.CCP_SOURCES_CONFIG,
            '/tmp/3galera_1comp.yaml'])

        underlay.sudo_check_call("pip install python-openstackclient",
                                 host=config.k8s.kube_host)
        show_step(3)
        ccpcluster.deploy(params={"config-file": "./config_1.yaml"},
                          use_cli_params=True)
        show_step(4)
        post_os_deploy_checks.check_jobs_status(k8s_actions.api, timeout=2000)
        post_os_deploy_checks.check_pods_status(k8s_actions.api)
        show_step(5)
        # todo: add invocation of galera checker script
        show_step(6)
        remote.check_call(
            "source openrc-{}; bash fuel-ccp/tools/deploy-test-vms.sh -a"
            " create".format(
                general_config["kubernetes"]["namespace"]),
            timeout=600)

    @pytest.mark.revert_snapshot(name="galera_cluster")
    @pytest.mark.fail_snapshot
    @pytest.mark.galera_shutdown
    @pytest.mark.galera
    def test_galera_shutdown_node(self, hardware, underlay, config,
                                  ccpcluster, k8s_actions, show_step):
        """Shutdown galera node

        Scenario:
        1. Revert snapshot with deployed galera
        2. Shutdown one galera node
        3. Check galera state
        4. Create 2 vms

        Duration 30 min
        """
        show_step(2)
        hardware.shutdown_node_by_ip(underlay.node_names()[1])
        show_step(3)
        # todo: add wait for galera to assemble when galera_checker is ready
        remote = underlay.remote(host=config.k8s.kube_host)
        show_step(4)
        remote.check_call(
            "source openrc-{}; bash fuel-ccp/tools/deploy-test-vms.sh -a"
            " create".format(
                settings.CCP_CONF["kubernetes"]["namespace"]),
            timeout=600)

    @pytest.mark.revert_snapshot(name="galera_cluster")
    @pytest.mark.fail_snapshot
    @pytest.mark.galera_cold_restart
    @pytest.mark.galera
    def test_galera_cold_restart_node(self, hardware, underlay, config,
                                      ccpcluster, k8s_actions, show_step):
        """Cold restart galera node

        Scenario:
        1. Revert snapshot with deployed galera
        2. Cold restart one galera node
        3. Check galera state
        4. Create 2 vms

        Duration 30 min
        """
        show_step(2)
        hardware.shutdown_node_by_ip(underlay.node_names()[1])
        hardware.start_node_by_ip(underlay.host_by_node_name('slave-0'))
        show_step(3)
        # todo: add wait for galera to assemble when galera_checker is ready
        remote = underlay.remote(host=config.k8s.kube_host)
        show_step(4)
        remote.check_call(
            "source openrc-{}; bash fuel-ccp/tools/deploy-test-vms.sh -a"
            " create".format(
                settings.CCP_CONF["kubernetes"]["namespace"]),
            timeout=600)

    @pytest.mark.revert_snapshot(name="galera_cluster")
    @pytest.mark.fail_snapshot
    @pytest.mark.galera_poweroff
    @pytest.mark.galera
    def test_galera_poweroff_node(self, hardware, underlay, config,
                                  ccpcluster, k8s_actions, show_step):
        """Poweroff galera node

        Scenario:
        1. Revert snapshot with deployed galera
        2. Poweroff one galera node
        3. Check galera state
        4. Create 2 vms

        Duration 30 min
        """
        galera_node = underlay.node_names()[1]
        galera_node_ip = underlay.host_by_node_name(galera_node)
        show_step(2)
        underlay.sudo_check_call('shutdown +1', node_name=galera_node)
        hardware.shutdown_node_by_ip(galera_node_ip)
        hardware.wait_node_is_offline(galera_node_ip, 90)
        show_step(3)
        # todo: add wait for galera to assemble when galera_checker is ready
        remote = underlay.remote(host=config.k8s.kube_host)
        show_step(4)
        remote.check_call(
            "source openrc-{}; bash fuel-ccp/tools/deploy-test-vms.sh -a"
            " create".format(
                settings.CCP_CONF["kubernetes"]["namespace"]),
            timeout=600)

    @pytest.mark.revert_snapshot(name="galera_cluster")
    @pytest.mark.fail_snapshot
    @pytest.mark.galera_soft_reboot
    @pytest.mark.galera
    def test_galera_soft_reboot_node(self, hardware, underlay, config,
                                     ccpcluster, k8s_actions, show_step):
        """Soft reboot galera node

        Scenario:
        1. Revert snapshot with deployed galera
        2. Soft reboot one galera node
        3. Check galera state
        4. Create 2 vms

        Duration 30 min
        """
        galera_node = underlay.node_names()[1]
        galera_node_ip = underlay.host_by_node_name(galera_node)
        show_step(2)
        underlay.sudo_check_call('shutdown +1', node_name=galera_node)
        hardware.shutdown_node_by_ip(galera_node_ip)
        hardware.wait_node_is_offline(galera_node_ip, 90)
        hardware.start_node_by_ip(galera_node_ip)
        hardware.wait_node_is_online(galera_node_ip, 180)
        show_step(3)
        # todo: add wait for galera to assemble when galera_checker is ready
        remote = underlay.remote(host=config.k8s.kube_host)
        show_step(4)
        remote.check_call(
            "source openrc-{}; bash fuel-ccp/tools/deploy-test-vms.sh -a"
            " create".format(
                settings.CCP_CONF["kubernetes"]["namespace"]),
            timeout=600)

    @pytest.mark.revert_snapshot(name="galera_cluster")
    @pytest.mark.fail_snapshot
    @pytest.mark.galera_cluster_shutdown
    @pytest.mark.galera
    def test_galera_cluster_shutdown(self, hardware, underlay, config,
                                     ccpcluster, k8s_actions, show_step):
        """Galera cluster shutdown

        Scenario:
        1. Revert snapshot with deployed galera
        2. Shutdown all galera nodes and start them one by one
        3. Check galera state
        4. Create 2 vms

        Duration 30 min
        """
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
        # todo: add wait for galera to assemble when galera_checker is ready
        remote = underlay.remote(host=config.k8s.kube_host)
        show_step(4)
        remote.check_call(
            "source openrc-{}; bash fuel-ccp/tools/deploy-test-vms.sh -a"
            " create".format(
                settings.CCP_CONF["kubernetes"]["namespace"]),
            timeout=600)

    @pytest.mark.revert_snapshot(name="galera_cluster")
    @pytest.mark.fail_snapshot
    @pytest.mark.galera_scale_up_down
    @pytest.mark.galera
    def test_galera_scale(self, hardware, underlay, config,
                                     ccpcluster, k8s_actions, show_step):
        """Galera cluster scale

        Scenario:
        1. Revert snapshot with deployed galera
        2. Scale up galera to 5 replicas
        3. Check galera state
        4. Check number of galera pods
        5. Create 2 vms
        6. Scale down galera to 3 replicas
        7. Check galera state
        8. Check number of galera pods
        9. Create 2 vms

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
        # todo: add invocation of galera checker script
        show_step(4)
        galera_pods = \
            k8s_actions.get_pods_number('galera',
                                        settings.
                                        CCP_CONF['kubernetes']['namespace'])
        assert galera_pods == 5,\
            "Expcted tp have 5 galera pods, got {}".format(galera_pods)

        show_step(5)
        remote = underlay.remote(host=config.k8s.kube_host)
        remote.check_call(
            "source openrc-{}; bash fuel-ccp/tools/deploy-test-vms.sh -a"
            " create".format(
                settings.CCP_CONF["kubernetes"]["namespace"]),
            timeout=600)
        show_step(6)
        with underlay.yaml_editor('./config_1.yaml',
                                  host=config.k8s.kube_host) as editor:
            editor.content['replicas']['galera'] = 3
        ccpcluster.deploy(params={"config-file": "./config_1.yaml"},
                          use_cli_params=True)
        post_os_deploy_checks.check_jobs_status(k8s_actions.api, timeout=2000)
        post_os_deploy_checks.check_pods_status(k8s_actions.api)
        show_step(7)
        # todo: add invocation of galera checker script
        show_step(8)
        galera_pods = \
            k8s_actions.get_pods_number('galera',
                                        settings.
                                        CCP_CONF['kubernetes']['namespace'])
        assert galera_pods == 3,\
            "Expcted tp have 3 galera pods, got {}".format(galera_pods)
        show_step(9)
        remote.check_call(
            "source openrc-{}; bash fuel-ccp/tools/deploy-test-vms.sh -a"
            " create".format(
                settings.CCP_CONF["kubernetes"]["namespace"]),
            timeout=600)
