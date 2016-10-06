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

from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import post_os_deploy_checks

LOG = logger.logger
LOG.addHandler(logger.console)


class TestDeployHeat(object):
    @pytest.mark.revert_snapshot(settings.PRECOMMIT_SNAPSHOT_NAME)
    @pytest.mark.heat_component
    def test_heat_component(self, ccpcluster, k8s_actions, rally):
        """Heat pre-commit test
        Scenario:
        1. Fetch all repos
        2. Update heat source form local path
        3. Build images
        4. Deploy openstack
        5. check jobs are ready
        6. Check ppods are ready
        7. Run heat tests
        Duration 60 min
        """
        LOG.info('Create registry')
        if settings.REGISTRY == '127.0.0.1:31500':
            k8s_actions.create_registry()

        if settings.BUILD_IMAGES:
            LOG.info('Fetch repositories...')
            ccpcluster.fetch()
            LOG.info('Update service...')
            ccpcluster.update_service('heat')
            LOG.info('Build images')
            ccpcluster.build('base-tools', suppress_output=False)
            ccpcluster.build(suppress_output=False)

        LOG.info('Deploy services')
        ccpcluster.deploy()
        LOG.info('Check jobs are ready')
        rally.prepare()
        rally.pull_image()
        rally.run()
        post_os_deploy_checks.check_jobs_status(k8s_actions.api)
        LOG.info('Check pods are running')
        post_os_deploy_checks.check_pods_status(k8s_actions.api)

        rally.run_tempest('--regex tempest.api.orchestration')
