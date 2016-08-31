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
from fuel_ccp_tests.managers import envmanager_devops
from fuel_ccp_tests.managers import envmanager_empty
from fuel_ccp_tests.managers import underlay_ssh_manager

LOG = logger.logger


@pytest.fixture(scope='function')
def deploy_openstack_default(revert_snapshot, config, underlay,
                             k8s_actions, ccpcluster):
    """Deploy openstack
    Scenario:
    1. Fetch all repos
    2. Update heat source form local path
    3. Build images
    4. Deploy openstack
    5. check jobs are ready
    6. check pods are ready
    Duration 60 min
    """
    if revert_snapshot and config.os.running == False:
        LOG.info("Deploy openstack")
        if settings.BUILD_IMAGES:
            k8s_actions.create_registry()
            ccpcluster.build()
            ccpcluster.deploy()
    else:
        if not settings.REGISTRY:
            raise ValueError("The REGISTRY variable should be set with "
                             "external registry address, "
                             "current value {0}".format(settings.REGISTRY))
    if config.os.running == False:
        post_os_deploy_checks.check_jobs_status(k8s_actions.api, timeout=3600)
        post_os_deploy_checks.check_pods_status(k8s_actions.api, timeout=3600)
        config.os.running = True
        revert_snapshot.create_snapshot(ext.SNAPSHOT.os_deployed)
