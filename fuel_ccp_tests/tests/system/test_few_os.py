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
import copy
import os
import pytest

import base_test
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import post_os_deploy_checks

LOG = logger.logger


class TestDeployTwoOS(base_test.SystemBaseTest):
    """Deploy Two OpenStack clusters with CCP

    """
    @pytest.mark.deploy_two_os
    @pytest.mark.fail_snapshot
    @pytest.mark.system_few_os
    def test_deploy_two_os(self, underlay, config, ccpcluster, k8s_actions):
        """Deploy base environment

        Scenario:
        1. Revert snapshot
        2. Install microservices
        3. Deploy one OS cluster
        4. Check deployment
        5. Create 2 vms
        6. Deploy another OS cluster on different nodes
        7. Check deployment
        8. Create 2 vms

        Duration 90 min
        """
        if settings.REGISTRY == "127.0.0.1:31500":
            k8s_actions.create_registry()
            ccpcluster.build()
        topology_path = \
            os.getcwd() + '/fuel_ccp_tests/templates/ccp_deploy_topology/' \
                          '1ctrl_1comp.yaml'
        remote = underlay.remote(host=config.k8s.kube_host)
        remote.upload(topology_path, '/tmp')
        ccpcluster.put_yaml_config('./config_1.yaml', settings.CCP_CONF)
        ccpcluster.add_includes('./config_1.yaml', [
            settings.CCP_DEPLOY_CONFIG,
            settings.CCP_SOURCES_CONFIG,
            '/tmp/1ctrl_1comp.yaml'])

        underlay.sudo_check_call("pip install python-openstackclient",
                                 host=config.k8s.kube_host)
        ccpcluster.deploy(params={"config-file": "./config_1.yaml"})
        post_os_deploy_checks.check_jobs_status(k8s_actions.api)
        post_os_deploy_checks.check_pods_status(k8s_actions.api)
        remote.check_call(
            "source openrc-{}; bash fuel-ccp/tools/deploy-test-vms.sh -a"
            " create".format(
                settings.CCP_CONF["kubernetes"]["namespace"]),
            timeout=600)

        topology_path = \
            os.getcwd() + '/fuel_ccp_tests/templates/ccp_deploy_topology/' \
                          '1ctrl_1comp_diff.yaml'
        remote.upload(topology_path, '/tmp')
        conf = copy.deepcopy(settings.CCP_CONF)
        conf['kubernetes']['namespace'] = 'ccp-second'
        ccpcluster.put_yaml_config('./config_2.yaml', conf)
        ccpcluster.add_includes('./config_2.yaml', [
            settings.CCP_DEPLOY_CONFIG,
            settings.CCP_SOURCES_CONFIG,
            '/tmp/1ctrl_1comp_diff.yaml'])

        ccpcluster.deploy(params={"config-file": "./config_2.yaml"})
        post_os_deploy_checks.check_jobs_status(k8s_actions.api,
                                                namespace="ccp-second")
        post_os_deploy_checks.check_pods_status(k8s_actions.api,
                                                namespace="ccp-second")
        remote.check_call(
            "source openrc-{0}; bash fuel-ccp/tools/deploy-test-vms.sh -k {0}"
            " -a create".format(
                settings.CCP_CONF["kubernetes"]["namespace"]),
            timeout=600)

    @pytest.mark.snapshot_needed(name="two_os")
    @pytest.mark.deploy_two_os
    @pytest.mark.fail_snapshot
    @pytest.mark.system_few_os
    def test_deploy_two_os_same_ctrl(self, underlay, config,
                                     ccpcluster, k8s_actions):
        """Deploy base environment

        Scenario:
        1. Revert snapshot
        2. Install microservices
        3. Deploy one OS cluster
        4. Check deployment
        5. Create 2 vms
        6. Deploy another OS cluster, controller on the same node
        7. Check deployment
        8. Create 2 vms

        Duration 90 min
        """
        if settings.REGISTRY == "127.0.0.1:31500":
            k8s_actions.create_registry()
            ccpcluster.build()
        topology_path = \
            os.getcwd() + '/fuel_ccp_tests/templates/ccp_deploy_topology/' \
                          '1ctrl_1comp.yaml'
        remote = underlay.remote(host=config.k8s.kube_host)
        remote.upload(topology_path, '/tmp')
        ccpcluster.put_yaml_config('./config_1.yaml', settings.CCP_CONF)
        ccpcluster.add_includes('./config_1.yaml', [
            settings.CCP_DEPLOY_CONFIG,
            settings.CCP_SOURCES_CONFIG,
            '/tmp/1ctrl_1comp.yaml'])

        underlay.sudo_check_call("pip install python-openstackclient",
                                 host=config.k8s.kube_host)
        ccpcluster.deploy(params={"config-file": "./config_1.yaml"})
        post_os_deploy_checks.check_jobs_status(k8s_actions.api)
        post_os_deploy_checks.check_pods_status(k8s_actions.api)
        remote.check_call(
            "source openrc-{}; bash fuel-ccp/tools/deploy-test-vms.sh -a"
            " create".format(
                settings.CCP_CONF["kubernetes"]["namespace"]),
            timeout=600)

        topology_path = \
            os.getcwd() + '/fuel_ccp_tests/templates/ccp_deploy_topology/' \
                          '1ctrl_1comp_same.yaml'
        remote.upload(topology_path, '/tmp')
        conf = copy.deepcopy(settings.CCP_CONF)
        conf['kubernetes']['namespace'] = 'ccp-second'
        ccpcluster.put_yaml_config('./config_2.yaml', conf)
        ccpcluster.add_includes('./config_2.yaml', [
            settings.CCP_DEPLOY_CONFIG,
            settings.CCP_SOURCES_CONFIG,
            '/tmp/1ctrl_1comp_same.yaml'])

        ccpcluster.deploy(params={"config-file": "./config_2.yaml"})
        post_os_deploy_checks.check_jobs_status(k8s_actions.api,
                                                namespace="ccp-second")
        post_os_deploy_checks.check_pods_status(k8s_actions.api,
                                                namespace="ccp-second")
        remote.check_call(
            "source openrc-{0}; bash fuel-ccp/tools/deploy-test-vms.sh -k {0}"
            " -a create".format(
                settings.CCP_CONF["kubernetes"]["namespace"]),
            timeout=600)

    @pytest.mark.deploy_two_os
    @pytest.mark.fail_snapshot
    @pytest.mark.system_few_os
    def test_deploy_3_ctrl(self, underlay, config, ccpcluster, k8s_actions):
        """Deploy base environment

        Scenario:
        1. Revert snapshot
        2. Install microservices
        3. Deploy one OS cluster with 1 controller
        4. Check deployment
        5. Create flavor
        6. Deploy another OS cluster with 1 controller
        7. Check deployment
        8. Create flavor
        9. Deploy another OS cluster with 1 controller
        10. Check deployment
        11. Create flavor

        Duration 60 min
        """
        if settings.REGISTRY == "127.0.0.1:31500":
            k8s_actions.create_registry()
            ccpcluster.build()
        topology_path = \
            os.getcwd() + '/fuel_ccp_tests/templates/ccp_deploy_topology/' \
                          '1ctrl.yaml'
        remote = underlay.remote(host=config.k8s.kube_host)
        remote.upload(topology_path, '/tmp')
        ccpcluster.put_yaml_config('./config_1.yaml', settings.CCP_CONF)
        ccpcluster.add_includes('./config_1.yaml', [
            settings.CCP_DEPLOY_CONFIG,
            settings.CCP_SOURCES_CONFIG,
            '/tmp/1ctrl.yaml'])

        underlay.sudo_check_call("pip install python-openstackclient",
                                 host=config.k8s.kube_host)
        ccpcluster.deploy(params={"config-file": "./config_1.yaml"})
        post_os_deploy_checks.check_jobs_status(k8s_actions.api)
        post_os_deploy_checks.check_pods_status(k8s_actions.api)
        remote.check_call(
            "source openrc-{}; openstack flavor create"
            " test".format(settings.CCP_CONF["kubernetes"]["namespace"]),
            timeout=600)

        remote.check_call("sed -i '/node[1-9]/c\  node2:' /tmp/1ctrl.yaml")

        conf = copy.deepcopy(settings.CCP_CONF)
        conf['kubernetes']['namespace'] = 'ccp-second'
        ccpcluster.put_yaml_config('./config_2.yaml', conf)
        ccpcluster.add_includes('./config_2.yaml', [
            settings.CCP_DEPLOY_CONFIG,
            settings.CCP_SOURCES_CONFIG,
            '/tmp/1ctrl.yaml'])

        ccpcluster.deploy(params={"config-file": "./config_2.yaml"})
        post_os_deploy_checks.check_jobs_status(k8s_actions.api,
                                                namespace="ccp-second")
        post_os_deploy_checks.check_pods_status(k8s_actions.api,
                                                namespace="ccp-second")
        remote.check_call(
            "source openrc-ccp-second;"
            " openstack flavor create test",
            timeout=600)
        remote.check_call("sed -i '/node[1-9]/c\  node3:' /tmp/1ctrl.yaml")
        conf = copy.deepcopy(settings.CCP_CONF)
        conf['kubernetes']['namespace'] = 'ccp-third'
        ccpcluster.put_yaml_config('./config_3.yaml', conf)
        ccpcluster.add_includes('./config_3.yaml', [
            settings.CCP_DEPLOY_CONFIG,
            settings.CCP_SOURCES_CONFIG,
            '/tmp/1ctrl.yaml'])
        ccpcluster.deploy(params={"config-file": "./config_3.yaml"})
        post_os_deploy_checks.check_jobs_status(k8s_actions.api,
                                                namespace="ccp-third")
        post_os_deploy_checks.check_pods_status(k8s_actions.api,
                                                namespace="ccp-third")
        remote.check_call(
            "source openrc-ccp-third;"
            " openstack flavor create test",
            timeout=600)

    @pytest.mark.revert_snapshot(name="two_os")
    @pytest.mark.deploy_two_os
    @pytest.mark.fail_snapshot
    @pytest.mark.system_few_os
    def test_deploy_two_os_kill_keystone(self, underlay, config, k8s_actions):
        """Deploy base environment

        Scenario:
        1. Revert snapshot with 2 deployed OS
        2. Delete keystone service from first deployment
        3. Check second cluster is operational

        Duration 15 min
        """
        remote = underlay.remote(host=config.k8s.kube_host)
        k8s_actions.api.services.delete(
            name='keystone',
            namespace=settings.CCP_CONF["kubernetes"]["namespace"])
        remote.check_call(
            "source openrc-{0}; bash fuel-ccp/tools/deploy-test-vms.sh -k {0}"
            " -a create".format(
                settings.CCP_CONF["kubernetes"]["namespace"]),
            timeout=600)

    @pytest.mark.revert_snapshot(name="two_os")
    @pytest.mark.deploy_two_os
    @pytest.mark.fail_snapshot
    @pytest.mark.system_few_os
    def test_deploy_two_os_kill_nova(self, underlay, config, k8s_actions):
        """Deploy base environment

        Scenario:
        1. Revert snapshot with 2 deployed OS
        2. Delete nova-api service from first deployment
        3. Check second cluster is operational

        Duration 90 min
        """
        remote = underlay.remote(host=config.k8s.kube_host)
        k8s_actions.api.services.delete(
            name='nova-api',
            namespace=settings.CCP_CONF["kubernetes"]["namespace"])
        remote.check_call(
            "source openrc-{0}; bash fuel-ccp/tools/deploy-test-vms.sh -k {0}"
            " -a create".format(
                settings.CCP_CONF["kubernetes"]["namespace"]),
            timeout=600)
