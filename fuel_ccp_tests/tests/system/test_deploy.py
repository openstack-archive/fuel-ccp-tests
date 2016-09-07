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

import base_test
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import post_os_deploy_checks
from fuel_ccp_tests.helpers import ext

LOG = logger.logger


class TestDeployOpenstack(base_test.SystemBaseTest):
    """Deploy OpenStack with CCP

       pytest.mark: deploy_openstack
    """

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
    @pytest.mark.deploy_openstack
    def test_fuel_ccp_deploy_microservices(self, ccpcluster, k8s_actions):
        """Deploy base environment

        Scenario:
        1. Revert snapshot
        2. Install microservices
        3. Deploy environment
        4. Check deployment

        Duration 35 min
        """
        if settings.BUILD_IMAGES:
            k8s_actions.create_registry()
            ccpcluster.build()
        else:
            if not settings.REGISTRY:
                raise ValueError("The REGISTRY variable should be set with "
                                 "external registry address, "
                                 "current value {0}".format(settings.REGISTRY))
        ccpcluster.deploy()
        post_os_deploy_checks.check_jobs_status(k8s_actions.api)
        post_os_deploy_checks.check_pods_status(k8s_actions.api)

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
    @pytest.mark.component
    @pytest.mark.dry_run
    def test_fuel_ccp_dry_run(self, ccpcluster, k8s_actions):
        """Deploy base environment

        Scenario:
        1. Revert snapshot
        2. Install microservices
        3. Create yaml templates
        4. Deploy environment
        4. Check deployment

        Duration 35 min
        """
        k8s_actions.create_registry()
        ccpcluster.build()
        export_dir = "/home/{user}/export".format(user=settings.SSH_LOGIN)
        ccpcluster.dry_deploy(export_dir=export_dir)
        k8s_actions.create_objects(folder=export_dir)
        post_os_deploy_checks.check_jobs_status(k8s_actions.api)
        post_os_deploy_checks.check_pods_status(k8s_actions.api)
