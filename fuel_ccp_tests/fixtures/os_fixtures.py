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

from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests.helpers import post_os_deploy_checks
from fuel_ccp_tests.managers.osmanager import OSManager

LOG = logger.logger


@pytest.fixture(scope='function')
def os_deployed(ccpcluster,
                hardware,
                underlay,
                revert_snapshot,
                config,
                k8s_actions):
    """Deploy openstack
    """
    # If no snapshot was reverted, then try to revert the snapshot
    # that belongs to the fixture.
    # Note: keep fixtures in strict dependences from each other!
    if not revert_snapshot:
        if hardware.has_snapshot(ext.SNAPSHOT.os_deployed) and \
                hardware.has_snapshot_config(ext.SNAPSHOT.os_deployed):
            hardware.revert_snapshot(ext.SNAPSHOT.os_deployed)

    osmanager = OSManager(config, underlay, k8s_actions, ccpcluster)
    if not config.os.running:
        LOG.info("Preparing openstack log collector fixture...")
        topology = None
        if config.os_deploy.stacklight_enable:
            topology = ('/fuel_ccp_tests/templates/k8s_templates/'
                        'stacklight_topology.yaml')
        osmanager.install_os(topology=topology)
        hardware.create_snapshot(ext.SNAPSHOT.os_deployed)
    else:
        LOG.info("Openstack allready installed and running...")
        osmanager.check_os_ready()


@pytest.fixture(scope='function')
def galera_deployed(ccpcluster,
                    hardware,
                    underlay,
                    revert_snapshot,
                    config,
                    k8s_actions):
    """Deploy galera cluster
    """
    # If no snapshot was reverted, then try to revert the snapshot
    # that belongs to the fixture.
    # Note: keep fixtures in strict dependences from each other!
    if not revert_snapshot:
        if hardware.has_snapshot(ext.SNAPSHOT.os_galera_deployed) and \
                hardware.has_snapshot_config(ext.SNAPSHOT.os_galera_deployed):
            hardware.revert_snapshot(ext.SNAPSHOT.os_galera_deployed)
    if not config.os.running:
        general_config = deepcopy(settings.CCP_CONF)
        general_config['replicas'] = {'galera': 3}
        if settings.BUILD_IMAGES:
            k8s_actions.create_registry()
            ccpcluster.build()
        topology_path = \
            os.getcwd() + '/fuel_ccp_tests/templates/k8s_templates/' \
                          '3galera_1comp.yaml'
        remote = underlay.remote(host=config.k8s.kube_host)
        remote.upload(topology_path, '/tmp')
        ccpcluster.put_yaml_config('./config_1.yaml', general_config)
        ccpcluster.add_includes('./config_1.yaml', [
            settings.CCP_DEPLOY_CONFIG,
            settings.CCP_SOURCES_CONFIG,
            '/tmp/3galera_1comp.yaml'])

        underlay.sudo_check_call("pip install python-openstackclient",
                                 host=config.k8s.kube_host)
        ccpcluster.deploy(params={"config-file": "./config_1.yaml"},
                          use_cli_params=True)
        post_os_deploy_checks.check_jobs_status(k8s_actions.api, timeout=2000)
        post_os_deploy_checks.check_pods_status(k8s_actions.api)
        # todo: add invocation of galera checker script
        remote.check_call(
            "source openrc-{}; bash fuel-ccp/tools/deploy-test-vms.sh -a"
            " create".format(
                settings.CCP_CONF["kubernetes"]["namespace"]),
            timeout=600)

        config.os.running = True
        hardware.create_snapshot(ext.SNAPSHOT.os_galera_deployed)
