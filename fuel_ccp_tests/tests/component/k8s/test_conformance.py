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

from fuel_ccp_tests.helpers import _subprocess_runner
from fuel_ccp_tests.helpers import exceptions
from fuel_ccp_tests import logger

LOG = logger.logger


@pytest.mark.k8s_conformance
@pytest.mark.component_k8s
class TestK8sConformance(object):

    required_settings = [
        "E2E_CONFORMANCE_IMAGE"
    ]

    @pytest.mark.fail_snapshot
    @pytest.mark.dashboard_exists
    @pytest.mark.usefixtures("check_settings_missing", "k8scluster")
    def test_k8s_conformance(self, underlay, config):
        """Run k8s conformance tests.

        Requires path to the image to be set via environment variable
        E2E_CONFORMANCE_IMAGE

        Scenario:
            1. Get or deploy k8s environment.
            2. Run conformance tests
        """
        LOG.info("Running e2e conformance tests")
        remote = underlay.remote(host=config.k8s.kube_host)
        cmd = 'docker run --rm --net=host ' \
              '-e API_SERVER="http://127.0.0.1:8080" ' \
              '{image} >> e2e-conformance.log'.format(
                  image=config.k8s_deploy.e2e_conformance_image
              )
        result = remote.execute(
            cmd,
            timeout=config.k8s_deploy.e2e_conformance_timeout,
            verbose=True)

        cmd = "mkdir -p logs"

        # FIXME Use Subprocess.execute instead of Subprocess.check_call until
        # check_call is not fixed (fuel-devops3.0.2)
        _subprocess_runner.Subprocess.execute(cmd, verbose=True)

        remote.download('/home/vagrant/e2e-conformance.log', 'logs/')

        expected_ec = [0]
        if result.exit_code not in expected_ec:
            raise exceptions.UnexpectedExitCode(
                cmd,
                result.exit_code,
                expected_ec,
                stdout=result.stdout_brief,
                stderr=result.stdout_brief)
