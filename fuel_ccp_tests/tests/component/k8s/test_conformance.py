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

from fuel_ccp_tests.helpers import _subprocess_runner
from fuel_ccp_tests.helpers import exceptions
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings

LOG = logger.logger


@pytest.mark.k8s_conformance
@pytest.mark.component_k8s
class TestK8sConformance(object):

    kube_settings = {
        "hyperkube_image_repo": settings.HYPERKUBE_IMAGE_REPO,
        "hyperkube_image_tag": settings.HYPERKUBE_IMAGE_TAG,
        "searchdomains": settings.SEARCH_DOMAINS,
    }

    @pytest.mark.fail_snapshot
    @pytest.mark.dashboard_exists
    def test_k8s_conformance(self, k8scluster):
        """Run k8s conformance tests

        Scenario:
            1. Get or deploy k8s environment.
            2. Run conformance tests
        """
        LOG.info("Running e2e conformance tests")

        params = ''
        params += 'export ADMIN_IP={}'.format(k8scluster.k8s_admin_ip)

        cmd = '{};{}'.format(params, settings.CONFORMANCE_RUNNER_SCRIPT)

        # Use Subprocess.execute instead of Subprocess.check_call until
        # check_call is not fixed (fuel-devops3.0.2)
        result = _subprocess_runner.Subprocess.execute(
            cmd,
            timeout=settings.CONFORMANCE_TIMEOUT,
            verbose=True)

        print(os.environ.get('ADMIN_IP'))
        expected_ec = [0]
        if result.exit_code not in expected_ec:
            raise exceptions.UnexpectedExitCode(
                cmd,
                result.exit_code,
                expected_ec,
                stdout=result.stdout_brief,
                stderr=result.stdout_brief)
