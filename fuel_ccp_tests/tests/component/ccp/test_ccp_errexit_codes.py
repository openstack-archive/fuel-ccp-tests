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
from fuel_ccp_tests.logger import logger


@pytest.yield_fixture(scope='function')
def admin_node(config, underlay, ccpcluster):
    """Return <remote> object to k8s admin node"""
    logger.info("Get SSH access to admin node")
    with underlay.remote(host=config.k8s.kube_host) as remote:
        yield remote


def clean_repos(node):
    cmd = 'rm ~/ccp-repos -rf'
    node.execute(cmd, verbose=True)


@pytest.mark.ccp_cli_errexit_codes
@pytest.mark.ccp_cli_error_in_fetch
@pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
@pytest.mark.component
class TestCppCliErrorInFetch(object):
    """Check exit codes when fetch is failing

       pytest.mark: ccp_cli_error_in_fetch
       module pytest.mark: ccp_cli_errexit_codes
    """

    @pytest.mark.fail_snapshot
    def test_wrong_repo_name(self, admin_node):
        cmd = ('ccp --repositories-names maria fetch')
        admin_node.check_call(cmd, expected=[1], verbose=True)

    @pytest.mark.fail_snapshot
    def test_wrong_repo_url(self, admin_node):
        cmd = ('ccp --repositories-fuel-ccp-debian-base '
               'http://example.org fetch')
        admin_node.check_call(cmd, expected=[1], verbose=True)
        clean_repos(admin_node)

    @pytest.mark.fail_snapshot
    def test_wrong_scheme_url(self, admin_node):
        cmd = ('ccp --repositories-fuel-ccp-debian-base '
               'htt://example.org fetch')
        admin_node.check_call(cmd, expected=[1], verbose=True)
        clean_repos(admin_node)


@pytest.mark.ccp_cli_errexit_codes
@pytest.mark.ccp_cli_build_exit_code
@pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
@pytest.mark.component
class TestCppCliBuildExitCode(object):
    """Check exit codes when build is failing

       pytest.mark: ccp_cli_build_exit_code
       module pytest.mark: ccp_cli_errexit_codes
    """
    @pytest.mark.fail_snapshot
    def test_nonexistent_repo_name(self, admin_node):
        cmd = 'ccp build --components example'
        admin_node.check_call(cmd, expected=[1], verbose=True)
        clean_repos(admin_node)

    @pytest.mark.fail_snapshot
    def test_error_build_image(self, admin_node):
        cmd = ('ccp --repositories-names fuel-ccp-debian-base fetch && '
               'echo "RUN exit 1" >> '
               '~/ccp-repos/fuel-ccp-debian-base/'
               'docker/base/Dockerfile.j2')
        admin_node.check_call(cmd, expected=[0], verbose=True)
        cmd = 'ccp build --components base'
        admin_node.check_call(cmd, expected=[1], verbose=True)
        clean_repos(admin_node)


@pytest.mark.ccp_cli_errexit_codes
@pytest.mark.ccp_cli_deploy_exit_code
@pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
@pytest.mark.component
class TestCppCliDeploy(object):
    """Check exit codes when deploy is failing

       pytest.mark: ccp_cli_deploy_exit_code
       module pytest.mark: ccp_cli_errexit_codes
    """

    @pytest.mark.fail_snapshot
    def test_nonexistent_repo_name(self, admin_node):
        cmd = 'ccp deploy --components example'
        admin_node.check_call(cmd, expected=[1], verbose=True)
        clean_repos(admin_node)


@pytest.mark.component
class TestCppCliErrorInShowDep(object):
    """Check exit codes when show-dep is failing"""

    @pytest.mark.ccp_cli_errexit_codes
    @pytest.mark.ccp_cli_deploy_exit_code
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
    def test_nonexistent_component_given(self, admin_node):
        """Test for ccp show-dep with non existing component exit code
        Scenario:
            1. exec ccp show-dep wrong_component
            2. Verify that exit code 1
        """
        logger.info("Error code for nonexistent component name")
        component = ["wrong_component"]
        expected = 1
        cmd = "ccp show-dep {}".format(component[0])
        admin_node.check_call(cmd, expected=[expected])

    @pytest.mark.ccp_cli_errexit_codes
    @pytest.mark.ccp_cli_deploy_exit_code
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
    def test_no_components_given(self, admin_node):
        """Test for ccp show-dep with no component given
        Scenario:
            1. exec ccp show-dep
            2. Verify that exit code 2
        """
        logger.info("Error code for no component")
        cmd = "ccp show-dep"
        expected = 2
        admin_node.check_call(cmd, expected=[expected])
