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


@pytest.yield_fixture(scope='session')
def admin_node(env, use_custom_yaml):
    logger.info("Fetch access to admin node")
    env.install_k8s(use_custom_yaml=use_custom_yaml)
    remote = env.node_ssh_client(
        env.k8s_nodes[0],
        login=settings.SSH_NODE_CREDENTIALS['login'],
        password=settings.SSH_NODE_CREDENTIALS['password'])

    ccp_repo_url = 'https://github.com/openstack/fuel-ccp.git'
    cmd = ('pip install --upgrade git+{}'.format(ccp_repo_url))
    with remote.get_sudo(remote):
        remote.check_call(cmd, verbose=True)
    yield remote
    remote.close()
    env.stop()


def clean_repos(admin_node):
    cmd = 'rm ~/microservices-repos -rf'
    admin_node.execute(cmd, verbose=True)


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
