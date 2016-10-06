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

from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import post_os_deploy_checks


class TestPreCommitSahara(object):
    """docstring for TestPreCommitSahara"""

    @pytest.mark.sahara_test
    @pytest.mark.sahara_component
    @pytest.mark.revert_snapshot(settings.PRECOMMIT_SNAPSHOT_NAME)
    def test_deploy_os_with_custom_sahara(
            self, ccpcluster, k8s_actions, underlay, rally):
        """
        Scenario:
            1. Install k8s
            2. Install fuel-ccp
            3. Fetch all repositories
            4. Fetch sahara from review
            5. Fetch containers from external registry
            6. Build sahara container
            7. Deploy Openstack
            8. Run tempest

        """

        if settings.REGISTRY == '127.0.0.1:31500':
            k8s_actions.create_registry()

        if settings.BUILD_IMAGES:
            ccpcluster.fetch()
            ccpcluster.update_service('sahara')
            ccpcluster.build('base-tools', suppress_output=False)
            ccpcluster.build(suppress_output=False)

        ccpcluster.deploy()
        rally.prepare()
        rally.pull_image()
        rally.run()

        post_os_deploy_checks.check_jobs_status(k8s_actions.api, timeout=1500,
                                                namespace='ccp')
        post_os_deploy_checks.check_pods_status(k8s_actions.api, timeout=2500,
                                                namespace='ccp')
        rally.run_tempest('--regex ^tempest.api.data_processing.*')
