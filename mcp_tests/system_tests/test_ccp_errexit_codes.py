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

from mcp_tests import settings
from mcp_tests.logger import logger


@pytest.yield_fixture(scope='module')
def admin_node(env_with_k8s_and_ccp):
    logger.info("Get SSH access to admin node")
    remote = env_with_k8s_and_ccp.node_ssh_client(
        env_with_k8s_and_ccp.k8s_nodes[0],
        login=settings.SSH_NODE_CREDENTIALS['login'],
        password=settings.SSH_NODE_CREDENTIALS['password'])
    yield remote
    remote.close()


def clean_repos(node):
    cmd = 'rm ~/microservices-repos -rf'
    node.execute(cmd, verbose=True)


class TestCppCliErrorInFetch(object):
    """Check exit codes when fetch is failing"""

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


class TestCppClinBuild(object):
    """Check exit codes when build is failing"""

    @pytest.mark.fail_snapshot
    def test_nonexistent_repo_name(self, admin_node):
        cmd = 'ccp build --components example'
        admin_node.check_call(cmd, expected=[1], verbose=True)
        clean_repos(admin_node)

    @pytest.mark.fail_snapshot
    def test_error_build_image(self, admin_node):
        cmd = ('ccp --repositories-names fuel-ccp-debian-base fetch && '
               'echo "RUN exit 1" >> '
               '~/microservices-repos/fuel-ccp-debian-base/'
               'docker/base/Dockerfile.j2')
        cmd = 'ccp build --components base'
        admin_node.check_call(cmd, expected=[1], verbose=True)
        clean_repos(admin_node)


class TestCppClinDeploy(object):
    """Check exit codes when deploy is failing"""

    @pytest.mark.fail_snapshot
    def test_nonexistent_repo_name(self, admin_node):
        cmd = 'ccp deploy --components example'
        admin_node.check_call(cmd, expected=[1], verbose=True)
        clean_repos(admin_node)
