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
import time
from devops.helpers import helpers

import base_test
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import post_os_deploy_checks
from fuel_ccp_tests.helpers import rabbit

LOG = logger.logger


class TestRabbitmq(base_test.SystemBaseTest):
    """ Galera scale and destructive scenarios

    """
    def get_pods(self, k8s):
        return \
            k8s.get_running_pods('rabbit',
                                 settings.CCP_CONF['kubernetes']['namespace'])

    @pytest.mark.fail_snapshot
    @pytest.mark.rabbitmq_deploy
    @pytest.mark.rabbitmq
    def test_rabbitmq(self, underlay, config,
                      k8s_actions, show_step,
                      os_deployed, rabbit_client):
        """Deploy rabbit cluster

        Scenario:
        1. Revert snapshot with deployed rabbit
        2. Check rabbit cluster state
        3. Check queue, messages replication

        Duration 30 min
        """
        show_step(2)
        show_step(3)
        namespace = settings.CCP_CONF["kubernetes"]["namespace"]
        remote = underlay.remote(host=config.k8s.kube_host)
        rabbit_pods = self.get_pods(k8s_actions)
        queue = rabbit_client.create_queue()
        message = rabbit_client.publish_message_to_queue(queue)
        rabbit_client.check_queue_message(message)
        for pod in rabbit_pods:
            rabbit_cluster_nodes = rabbit_client.list_nodes(
                remote, pod.name, namespace)
            assert rabbit_cluster_nodes == len(rabbit_pods),\
                "Expected to have {} nodes in cluster," \
                " got {}".format(len(rabbit_pods), rabbit_cluster_nodes)
            rabbit_client.check_queue_replicated(queue, remote,
                                                 pod.name, namespace)
        rabbit_client.delete_queue(queue)

    @pytest.mark.fail_snapshot
    @pytest.mark.rabbitmq_shutdown
    @pytest.mark.rabbitmq
    def test_rabbitmq_shutdown_node(self, hardware, underlay, config,
                                    ccpcluster, k8s_actions, show_step,
                                    os_deployed, rabbit_client):
        """Shutdown rabbitmq node

        Scenario:
        1. Revert snapshot with deployed rabbit
        2. Shutdown one rabbit node
        3. Check rabbit cluster state
        4. Check queue, messages replication
        5. Create 2 vms

        Duration 30 min
        """
        rabbit_node = underlay.node_names()[1]
        rabbit_node_ip = underlay.host_by_node_name(rabbit_node)
        namespace = settings.CCP_CONF["kubernetes"]["namespace"]
        rabbit_pods = self.get_pods(k8s_actions)
        show_step(2)
        hardware.shutdown_node_by_ip(rabbit_node_ip)
        show_step(3)

        helpers.wait(lambda: (len(self.get_pods(k8s_actions)) ==
                              len(rabbit_pods) - 1),
                     timeout=600,
                     timeout_msg='Timeout waiting for rabbit pod'
                                 ' to be terminated')
        pods_after_shutdown = self.get_pods(k8s_actions)
        remote = underlay.remote(host=config.k8s.kube_host)
        show_step(4)
        queue = rabbit_client.create_queue()
        message = rabbit_client.publish_message_to_queue(queue)
        rabbit_client.check_queue_message(message)
        for pod in pods_after_shutdown:
            rabbit_cluster_nodes = rabbit_client.list_nodes(
                remote, pod.name, namespace)
            assert rabbit_cluster_nodes == len(pods_after_shutdown),\
                "Expected to have {} nodes in cluster," \
                " got {}".format(len(pods_after_shutdown),
                                 rabbit_cluster_nodes)
            rabbit_client.check_queue_replicated(queue, remote,
                                                 pod.name, namespace)
        rabbit_client.delete_queue(queue)
        show_step(5)
        remote.check_call(
            "source openrc-{}; bash fuel-ccp/tools/deploy-test-vms.sh -a"
            " create".format(namespace), timeout=600)

    @pytest.mark.fail_snapshot
    @pytest.mark.rabbitmq_cold_restart
    @pytest.mark.rabbitmq
    def test_rabbitmq_cold_restart_node(self, hardware, underlay, config,
                                        ccpcluster, k8s_actions, show_step,
                                        os_deployed, rabbit_client):
        """Cold restart rabbitmq node

        Scenario:
        1. Revert snapshot with deployed rabbit
        2. Cold restart one rabbit node
        3. Check rabbit cluster state
        4. Check queue, messages replication
        5. Create 2 vms

        Duration 30 min
        """
        rabbit_node = underlay.node_names()[1]
        rabbit_node_ip = underlay.host_by_node_name(rabbit_node)
        namespace = settings.CCP_CONF["kubernetes"]["namespace"]
        rabbit_pods = self.get_pods(k8s_actions)

        show_step(2)
        hardware.shutdown_node_by_ip(rabbit_node_ip)
        hardware.wait_node_is_offline(rabbit_node_ip, 90)
        time.sleep(15)
        hardware.start_node_by_ip(rabbit_node_ip)
        hardware.wait_node_is_online(rabbit_node_ip, 180)
        show_step(3)

        helpers.wait(lambda: (len(self.get_pods(k8s_actions)) ==
                              len(rabbit_pods) - 1),
                     timeout=1200,
                     timeout_msg='Expected to have one pod destroyed'
                                 ' after reboot')

        helpers.wait(lambda: (len(self.get_pods(k8s_actions)) ==
                              len(rabbit_pods)),
                     timeout=1200,
                     timeout_msg='Expected pod to come back after reboot')

        pods_after_reboot = self.get_pods(k8s_actions)
        remote = underlay.remote(host=config.k8s.kube_host)
        show_step(4)
        queue = rabbit_client.create_queue()
        message = rabbit_client.publish_message_to_queue(queue)
        rabbit_client.check_queue_message(message)
        for pod in pods_after_reboot:
            rabbit_cluster_nodes = rabbit_client.list_nodes(
                remote, pod.name, namespace)
            assert rabbit_cluster_nodes == len(pods_after_reboot),\
                "Expected to have {} nodes in cluster," \
                " got {}".format(len(pods_after_reboot), rabbit_cluster_nodes)
            rabbit_client.check_queue_replicated(queue, remote,
                                                 pod.name, namespace)
        rabbit_client.delete_queue(queue)
        show_step(5)
        remote.check_call(
            "source openrc-{}; bash fuel-ccp/tools/deploy-test-vms.sh -a"
            " create".format(namespace), timeout=600)

    @pytest.mark.fail_snapshot
    @pytest.mark.rabbitmq_poweroff
    @pytest.mark.rabbitmq
    def test_rabbitmq_poweroff_node(self, hardware, underlay, config,
                                    ccpcluster, k8s_actions, show_step,
                                    os_deployed, rabbit_client):
        """Poweroff rabbit node

        Scenario:
        1. Revert snapshot with deployed rabbit
        2. Poweroff one rabbit node
        3. Check rabbit cluster state
        4. Check queue, messages replication
        5. Create 2 vms

        Duration 30 min
        """
        rabbit_node = underlay.node_names()[1]
        rabbit_node_ip = underlay.host_by_node_name(rabbit_node)
        namespace = settings.CCP_CONF["kubernetes"]["namespace"]
        rabbit_pods = self.get_pods(k8s_actions)
        show_step(2)
        underlay.sudo_check_call('shutdown +1', node_name=rabbit_node)
        hardware.shutdown_node_by_ip(rabbit_node_ip)
        hardware.wait_node_is_offline(rabbit_node_ip, 90)
        show_step(3)

        helpers.wait(lambda: (len(self.get_pods(k8s_actions)) ==
                              len(rabbit_pods) - 1),
                     timeout=600,
                     timeout_msg='Timeout waiting for rabbit pod'
                                 ' to be terminated')
        pods_after_reboot = self.get_pods(k8s_actions)
        remote = underlay.remote(host=config.k8s.kube_host)
        show_step(4)
        queue = rabbit_client.create_queue()
        message = rabbit_client.publish_message_to_queue(queue)
        rabbit_client.check_queue_message(message)
        for pod in pods_after_reboot:
            rabbit_cluster_nodes = rabbit_client.list_nodes(
                remote, pod.name, namespace)
            assert rabbit_cluster_nodes == len(pods_after_reboot),\
                "Expected to have {} nodes in cluster," \
                " got {}".format(len(pods_after_reboot), rabbit_cluster_nodes)
            rabbit_client.check_queue_replicated(queue, remote,
                                                 pod.name, namespace)
        rabbit_client.delete_queue(queue)
        show_step(5)
        remote.check_call(
            "source openrc-{}; bash fuel-ccp/tools/deploy-test-vms.sh -a"
            " create".format(namespace), timeout=600)

    @pytest.mark.fail_snapshot
    @pytest.mark.rabbitmq_soft_reboot
    @pytest.mark.rabbitmq
    def test_rabbitmq_soft_reboot_node(self, hardware, underlay, config,
                                       ccpcluster, k8s_actions, show_step,
                                       os_deployed, rabbit_client):
        """Soft reboot rabbitmq node

        Scenario:
        1. Revert snapshot with deployed rabbit
        2. Reboot one rabbit node
        3. Check rabbit cluster state
        4. Check queue, messages replication
        5. Create 2 vms

        Duration 30 min
        """
        rabbit_node = underlay.node_names()[1]
        rabbit_node_ip = underlay.host_by_node_name(rabbit_node)
        namespace = settings.CCP_CONF["kubernetes"]["namespace"]
        rabbit_pods = self.get_pods(k8s_actions)
        show_step(2)
        underlay.sudo_check_call('shutdown +1', node_name=rabbit_node)
        hardware.shutdown_node_by_ip(rabbit_node_ip)
        hardware.wait_node_is_offline(rabbit_node_ip, 90)
        time.sleep(15)
        hardware.start_node_by_ip(rabbit_node_ip)
        hardware.wait_node_is_online(rabbit_node_ip, 180)
        show_step(3)
        helpers.wait(lambda: (len(self.get_pods(k8s_actions)) ==
                              len(rabbit_pods)),
                     timeout=600,
                     timeout_msg='Timeout waiting for rabbit pod'
                                 ' to be terminated')
        pods_after_reboot = self.get_pods(k8s_actions)
        remote = underlay.remote(host=config.k8s.kube_host)
        show_step(4)
        queue = rabbit_client.create_queue()
        message = rabbit_client.publish_message_to_queue(queue)
        rabbit_client.check_queue_message(message)
        for pod in pods_after_reboot:
            rabbit_cluster_nodes = rabbit_client.list_nodes(
                remote, pod.name, namespace)
            assert rabbit_cluster_nodes == len(pods_after_reboot),\
                "Expected to have {} nodes in cluster," \
                " got {}".format(len(pods_after_reboot), rabbit_cluster_nodes)
            rabbit_client.check_queue_replicated(queue, remote,
                                                 pod.name, namespace)
        rabbit_client.delete_queue(queue)
        show_step(5)
        remote.check_call(
            "source openrc-{}; bash fuel-ccp/tools/deploy-test-vms.sh -a"
            " create".format(namespace), timeout=600)

    @pytest.mark.fail_snapshot
    @pytest.mark.rabbitmq_cluster_shutdown
    @pytest.mark.rabbitmq
    def test_rabbitmq_cluster_shutdown(self, hardware, underlay, config,
                                       ccpcluster, k8s_actions, show_step,
                                       os_deployed, rabbit_client):
        """Rabbitmq cluster shutdown

        Scenario:
        1. Revert snapshot with deployed rabbit
        2. Shutdown all rabbit nodes and start them one by one
        3. Check rabbit cluster state
        4. Check queue, messages replication
        5. Create 2 vms

        Duration 30 min
        """
        rabbit_nodes = underlay.node_names()[:3]
        namespace = settings.CCP_CONF["kubernetes"]["namespace"]
        rabbit_pods = self.get_pods(k8s_actions)
        rabbit_node_ips = []
        show_step(2)
        for rabbit_node in rabbit_nodes:
            rabbit_node_ip = underlay.host_by_node_name(rabbit_node)
            rabbit_node_ips.append(rabbit_node_ip)
            hardware.shutdown_node_by_ip(rabbit_node_ip)
            hardware.wait_node_is_offline(rabbit_node_ip, 90)
        for rabbit_ip in rabbit_node_ips:
            hardware.start_node_by_ip(rabbit_ip)
            hardware.wait_node_is_online(rabbit_ip, 180)
        show_step(3)
        post_os_deploy_checks.check_jobs_status(k8s_actions.api, timeout=2000)
        post_os_deploy_checks.check_pods_status(k8s_actions.api)
        pods_after_shutdown = self.get_pods(k8s_actions)
        assert len(rabbit_pods) == len(pods_after_shutdown),\
            "Different number of pods after shutdown, was {}," \
            " now {}".format(len(rabbit_pods), len(pods_after_shutdown))
        remote = underlay.remote(host=config.k8s.kube_host)
        show_step(4)
        host = config.k8s.kube_host
        rabbit_port = ''.join(remote.execute(
            "kubectl get service --namespace ccp rabbitmq -o yaml |"
            " awk '/nodePort: / {print $NF}'")['stdout'])
        rabbit_client = rabbit.RabbitClient(host, rabbit_port)
        queue = rabbit_client.create_queue()
        message = rabbit_client.publish_message_to_queue(queue)
        rabbit_client.check_queue_message(message)
        for pod in pods_after_shutdown:
            rabbit_cluster_nodes = rabbit_client.list_nodes(
                remote, pod.name, namespace)
            assert rabbit_cluster_nodes == len(pods_after_shutdown),\
                "Expected to have {} nodes in cluster," \
                " got {}".format(len(pods_after_shutdown),
                                 rabbit_cluster_nodes)
            rabbit_client.check_queue_replicated(queue, remote,
                                                 pod.name, namespace)
        rabbit_client.delete_queue(queue)
        remote.check_call(
            "source openrc-{}; bash fuel-ccp/tools/deploy-test-vms.sh -a"
            " create".format(namespace), timeout=600)

    @pytest.mark.fail_snapshot
    @pytest.mark.rabbitmq_scale_up_down
    @pytest.mark.rabbitmq
    def test_rabbitmq_scale(self, hardware, underlay, config,
                            ccpcluster, k8s_actions, show_step,
                            os_deployed, rabbit_client):
        """Rabbit cluster scale

        Scenario:
        1. Revert snapshot with deployed rabbit
        2. Scale up rabbit to 5 replicas
        3. Check rabbit state
        4. Check number of rabbit pods
        5. Create 2 vms
        6. Scale down rabbit to 3 replicas
        7. Check rabbit state
        8. Check number of rabbit pods
        9. Create 2 vms

        Duration 30 min
        """
        show_step(2)
        with underlay.yaml_editor(settings.CCP_DEPLOY_TOPOLOGY,
                                  host=config.k8s.kube_host) as editor:
            del editor.content['nodes']['node[1-3]']
            editor.content['nodes']['node[1-5]'] = {'roles': ['rabbitmq']}

        ccpcluster.deploy()
        post_os_deploy_checks.check_jobs_status(k8s_actions.api, timeout=2000)
        post_os_deploy_checks.check_pods_status(k8s_actions.api)
        namespace = settings.CCP_CONF["kubernetes"]["namespace"]
        remote = underlay.remote(host=config.k8s.kube_host)
        rabbit_pods = self.get_pods(k8s_actions)
        queue = rabbit_client.create_queue()
        message = rabbit_client.publish_message_to_queue(queue)
        rabbit_client.check_queue_message(message)
        for pod in rabbit_pods:
            rabbit_cluster_nodes = rabbit_client.list_nodes(
                remote, pod.name, namespace)
            assert rabbit_cluster_nodes == len(rabbit_pods),\
                "Expected to have {} nodes in cluster," \
                " got {}".format(len(rabbit_pods), rabbit_cluster_nodes)
            rabbit_client.check_queue_replicated(queue, remote,
                                                 pod.name, namespace)
        rabbit_client.delete_queue(queue)

        show_step(4)
        rabbit_pods = \
            k8s_actions.get_pods_number('rabbit', namespace)
        assert rabbit_pods == 5,\
            "Expcted to have 5 rabbit pods, got {}".format(rabbit_pods)

        show_step(5)
        remote.check_call(
            "source openrc-{}; bash fuel-ccp/tools/deploy-test-vms.sh -a"
            " create".format(namespace), timeout=600)
        show_step(6)
        with underlay.yaml_editor(settings.CCP_DEPLOY_TOPOLOGY,
                                  host=config.k8s.kube_host) as editor:
            del editor.content['nodes']['node[1-5]']
            editor.content['nodes']['node[1-3]'] = {'roles': ['rabbitmq']}

        ccpcluster.deploy()
        post_os_deploy_checks.check_jobs_status(k8s_actions.api, timeout=2000)
        post_os_deploy_checks.check_pods_status(k8s_actions.api)
        show_step(7)
        show_step(8)
        rabbit_pods = \
            k8s_actions.get_pods_number('rabbit', namespace)
        assert rabbit_pods == 3,\
            "Expcted to have 3 rabbit pods, got {}".format(rabbit_pods)
        show_step(9)
        remote.check_call(
            "source openrc-{}; bash fuel-ccp/tools/deploy-test-vms.sh -a"
            " create".format(namespace), timeout=600)

    @pytest.mark.fail_snapshot
    @pytest.mark.rabbitmq_node_replacement
    @pytest.mark.rabbitmq
    def test_rabbitmq_node_replacement(self, hardware, underlay, config,
                                       ccpcluster, k8s_actions, show_step,
                                       os_deployed, rabbit_client):
        """Rabbitmq node replacement

        Scenario:
        1. Revert snapshot with deployed rabbit
        2. Shutdown one rabbit node
        3. Add new rabbit node to config
        4. Re-deploy cluster
        5. Check rabbit cluster state
        6. Check queue, messages replication
        7. Create 2 vms

        Duration 30 min
        """
        rabbit_node = underlay.node_names()[1]
        rabbit_node_ip = underlay.host_by_node_name(rabbit_node)
        namespace = settings.CCP_CONF["kubernetes"]["namespace"]
        rabbit_pods = self.get_pods(k8s_actions)
        show_step(2)
        hardware.shutdown_node_by_ip(rabbit_node_ip)

        helpers.wait(lambda: (len(self.get_pods(k8s_actions)) ==
                              len(rabbit_pods) - 1),
                     timeout=600,
                     timeout_msg='Timeout waiting for rabbit pod'
                                 ' to be terminated')
        show_step(3)
        with underlay.yaml_editor(settings.CCP_DEPLOY_TOPOLOGY,
                                  host=config.k8s.kube_host) as editor:
            del editor.content['nodes']['node[1-3]']
            editor.content['nodes']['node[1-2]'] = {'roles': ['rabbitmq']}
            editor.content['nodes']['node4'] = {'roles': ['rabbitmq', 'etcd']}
        show_step(4)
        ccpcluster.deploy()
        post_os_deploy_checks.check_jobs_status(k8s_actions.api, timeout=2000)
        post_os_deploy_checks.check_pods_status(k8s_actions.api)

        pods_after_replacement = self.get_pods(k8s_actions)
        remote = underlay.remote(host=config.k8s.kube_host)
        show_step(6)
        queue = rabbit_client.create_queue()
        message = rabbit_client.publish_message_to_queue(queue)
        rabbit_client.check_queue_message(message)
        show_step(5)
        for pod in pods_after_replacement:
            rabbit_cluster_nodes = rabbit_client.list_nodes(
                remote, pod.name, namespace)
            assert rabbit_cluster_nodes == len(pods_after_replacement),\
                "Expected to have {} nodes in cluster," \
                " got {}".format(len(pods_after_replacement),
                                 rabbit_cluster_nodes)
            rabbit_client.check_queue_replicated(queue, remote,
                                                 pod.name, namespace)
        rabbit_client.delete_queue(queue)
        show_step(7)
        remote.check_call(
            "source openrc-{}; bash fuel-ccp/tools/deploy-test-vms.sh -a"
            " create".format(namespace), timeout=600)
