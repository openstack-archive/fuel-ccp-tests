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

from fuel_ccp_tests.helpers import post_os_deploy_checks
from fuel_ccp_tests.helpers import ext


class TestPreCommitNova(object):
    """docstring for TestPreCommitNova

    Scenario:
        1. Install k8s
        2. Install fuel-ccp
        3. Fetch all repositories
        4. Fetch nova from review
        5. Fetch containers from external registry
        6. Build nova container
        7. Deploy Openstack
        8. Run tempest
    """

    @pytest.mark.test_nova_on_commit
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
    def test_deploy_os_with_custom_nova(
            self, ccpcluster, k8s_actions, underlay, rally):
        """
        Scenario:
            1. Install k8s
            2. Install fuel-ccp
            3. Fetch repos
            4. Upload repo with changes
            5. Build components
            6. Deploy components
            7. Run compute tempest suite

        """

        k8s_actions.create_registry()
        ccpcluster.fetch()
        ccpcluster.update_service('nova')
        ccpcluster.build(suppress_output=False)
        ccpcluster.deploy()
        rally.prepare()
        rally.pull_image()
        rally.run()

        post_os_deploy_checks.check_jobs_status(k8s_actions.api)
        post_os_deploy_checks.check_pods_status(k8s_actions.api)
        rally.run_tempest('--regex  tempest.api.compute')
