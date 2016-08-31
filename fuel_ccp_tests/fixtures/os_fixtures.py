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

from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import post_os_deploy_checks


LOG = logger.logger


@pytest.fixture(scope='function')
def deploy_openstack_default(ccpcluster, hardware, revert_snapshot, config,
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
        pass


@pytest.fixture(scope='function')
def deploy_openstack_stacklight(ccpcluster, hardware, underlay,
                                revert_snapshot, config,
                                k8s_actions):
    """
    Deploy openstack with stacklight topology
    """
    LOG.info("Preparing openstack log collector fixture...")
    if revert_snapshot and not config.os.running:
        if settings.BUILD_IMAGES:
            LOG.info("Creating registry...")
            k8s_actions.create_registry()
            LOG.info("Building images...")
            ccpcluster.build()
        LOG.info("Pushing topology yaml...")
        LOG.warn("Patched topology used, workaround until kube 1.4 released")
        topology_path = \
            os.getcwd() + '/fuel_ccp_tests/templates/k8s_templates/' \
                          'topology-with-log-collector-no-stacklight.yaml'
        underlay.remote(
            host=config.k8s.kube_host).upload(
            topology_path,
            settings.CCP_CLI_PARAMS['deploy-config'])
        LOG.info("Deploy openstack")
        ccpcluster.deploy()
        LOG.info("Checking openstack jobs statuses...")
        post_os_deploy_checks.check_jobs_status(k8s_actions.api,
                                                timeout=3600)
        LOG.info("Checking openstack pods statuses...")
        post_os_deploy_checks.check_pods_status(k8s_actions.api,
                                                timeout=3600)
        config.os.running = True
        hardware.create_snapshot(ext.SNAPSHOT.os_stacklight_deployed)
    else:
        LOG.info("Openstack stacklight allready installed and running...")
