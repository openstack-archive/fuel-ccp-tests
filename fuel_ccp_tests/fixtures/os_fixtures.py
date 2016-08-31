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

from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import post_os_deploy_checks
from fuel_ccp_tests.managers.osmanager import OSManager
from time import sleep

LOG = logger.logger


@pytest.fixture(scope='function')
def os_deployed(ccpcluster, hardware, revert_snapshot, config,
                k8s_actions):
    """Deploy openstack with default topology
    """
    if revert_snapshot and not config.os.running:
        LOG.info("Deploy openstack")
        if settings.BUILD_IMAGES:
            k8s_actions.create_registry()
            ccpcluster.build()
        ccpcluster.deploy()
        post_os_deploy_checks.check_jobs_status(k8s_actions.api,
                                                timeout=3600)
        post_os_deploy_checks.check_pods_status(k8s_actions.api,
                                                timeout=3600)
        config.os.running = True
        hardware.create_snapshot(ext.SNAPSHOT.os_deployed)
    else:
        LOG.info("Openstack allready running")


@pytest.fixture(scope='function')
def os_deployed_stacklight(revert_snapshot,
                           hardware,
                           underlay,
                           config,
                           k8s_actions,
                           ccpcluster):
    """
    Deploy openstack with stacklight topology
    """
    osmanager = OSManager(config, underlay, k8s_actions, ccpcluster)
    if not config.os.running:
            LOG.info("Preparing openstack log collector fixture...")
            osmanager.install_os(
                topology='/fuel_ccp_tests/templates/k8s_templates/'
                         'topology-with-log-collector-no-stacklight.yaml'
            )
            hardware.create_snapshot(ext.SNAPSHOT.os_deployed_stacklight)
    else:
        LOG.info("Openstack stacklight allready installed and running...")
        osmanager.check_os_ready()
    # wait for elasticsearch index
    sleep(30)
