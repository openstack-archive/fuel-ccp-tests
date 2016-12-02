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
import re

import pytest

from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests import settings


@pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
class TestCppFetch(object):
    """Check ccp fetch feature
    """
    def test_ccp_fetch_default(self, config, underlay, ccpcluster, show_step):
        """Test for ccp Fetch all openstack repositories for master by http
         using fuel-ccp tool

        Scenario:
        1. exec ccp fetch with config repositories: protocol: http; port: 80
        2. Verify that downloaded repos match to default repos list
        """
        config_fetch = {
            'repositories': {
                'path': '{}'.format(settings.CCP_ENVIRONMENT_PARAMS[
                    "microservices_home"]),
                'protocol': 'http',
                'port': 80
            }
        }

        show_step(1)
        ccpcluster.fetch(params=config_fetch)

        show_step(2)
        cmd_fetched = \
            ('ls -d1 {}/* | xargs -n 1 basename'
             .format(settings.CCP_ENVIRONMENT_PARAMS["microservices_home"]))
        res = [s.strip() for s in underlay.check_call(
            cmd_fetched,
            verbose=True,
            host=config.k8s.kube_host)['stdout']]
        assert set(ext.DEFAULT_REPOS) == set(res), \
            'Unexpected repo\'s downloaded' \
            ' Expected count {}, actual {}'.format(
                len(ext.DEFAULT_REPOS), len(res))

    def test_ccp_fetch_some_via_ssh(self, config, underlay, ccpcluster,
                                    git_server_mock, show_step):
        """Test for ccp Fetch selected openstack repositories for master by ssh
         using fuel-ccp tool
         Precondition:
         ccp config:
           protocol: 'ssh'
           username: 'git'
           port: 2222
           hostname: 'localhost'
           project: git
           names:
             - fuel-ccp-debian-base
             - fuel-ccp-entrypoint

        Scenario:
        1. exec ccp fetch with config
        2. Verify that downloaded repos match to fuel-ccp-debian-base
            and  fuel-ccp-entrypointrepos list
        3. Verify that downloaded images from specified repository
        """
        expected = ['fuel-ccp-debian-base', 'fuel-ccp-entrypoint']

        config_fetch = {
            'repositories': {
                'path': '{}'.format(settings.CCP_ENVIRONMENT_PARAMS[
                    "microservices_home"]),
                'protocol': 'ssh',
                'username': 'git',
                'port': 2222,
                'hostname': 'localhost',
                'project': 'git',
                'names': [
                    'fuel-ccp-debian-base',
                    'fuel-ccp-entrypoint']
            }
        }

        show_step(1)
        ccpcluster.fetch(params=config_fetch)

        show_step(2)
        cmd_fetched = \
            ('ls -d1 {}/* | xargs -n 1 basename'
             .format(settings.CCP_ENVIRONMENT_PARAMS["microservices_home"]))
        res = [s.strip() for s in underlay.check_call(
            cmd_fetched,
            verbose=True,
            host=config.k8s.kube_host)['stdout']]
        assert set(expected) == set(res), 'Unexpected repo\'s downloaded' \
                                          ' Expected count {}, actual {}' \
            .format(len(expected), len(res))

        show_step(3)
        cmd_origin = (
            "cd {}/{} &&".format(settings.CCP_ENVIRONMENT_PARAMS[
                "microservices_home"], expected[0]) +
            "git remote show origin | grep ssh://git@localhost:2222")
        underlay.check_call(cmd_origin, verbose=True,
                            host=config.k8s.kube_host), \
            'Downloaded images are not from specified repository'

    def test_ccp_fetch_nonexisting_repo(self, config, underlay, ccpcluster,
                                        show_step):
        """Fetch nonexistent repo using fuel-ccp tool
        Precondition:
        ccp config:
          repositories:
            path: $microservices-home
            fuel_ccp_debian_base: fuel-ccp-not-exist

        Scenario:
        1. exec ccp fetch with config
        2. Verify fatal: repository 'fuel-ccp-not-exist' not exists"
        3. Verify no traceback printed for known negative case
        and exit code not 0
        4. Verify that no repositories fetched
        """
        exit_code = 1
        check_code_message = \
            'Unexpected exit code. Expected {}.'.format(exit_code)\
            + "Defect https://bugs.launchpad.net/fuel-ccp/+bug/1608981"
        err_message = \
            'fatal: repository \'fuel-ccp-not-exist\' does not exist'

        config_fetch = {
            'repositories': {
                'path': '{}'.format(settings.CCP_ENVIRONMENT_PARAMS[
                    "microservices_home"]),
                'fuel_ccp_debian_base': 'fuel-ccp-not-exist'
            }
        }

        show_step(1)
        res = ccpcluster.fetch(params=config_fetch,
                               expected=[exit_code],
                               error_info=check_code_message)

        show_step(2)
        assert err_message in res['stderr_str']

        show_step(3)
        assert 'Traceback' not in res['stderr_str'], (
            'traceback printed'
            'Defect https://bugs.launchpad.net/fuel-ccp/+bug/1620354')

        show_step(4)
        cmd_fetched = \
            ('ls -d1 {}/'
             .format(settings.CCP_ENVIRONMENT_PARAMS["microservices_home"]))
        error_info = \
            '{} - directory exist, but should not'.format(
                settings.CCP_ENVIRONMENT_PARAMS["microservices_home"])
        underlay.check_call(cmd_fetched, expected=[2], verbose=True,
                            host=config.k8s.kube_host, error_info=error_info)

    def test_ccp_fetch_incorrect_url(self, config, underlay, ccpcluster,
                                     show_step):
        """Fetch repo by incorrect url using ccp tool
        Precondition:
        ccp config:
          repositories:
            path: $microservices-home
            hostname: example.org

        Scenario:
            1. exec ccp fetch with config
            2. Verify fatal: repository 'http://example.org/' not found"
            3. Verify no traceback printed for known negative case
            and exit code not 0
            4. Verify that no repositories fetched
        """
        exit_code = 2
        err_message = 'fatal: repository \'.*\' not found'
        config_fetch = {
            'repositories': {
                'path': '{}'.format(settings.CCP_ENVIRONMENT_PARAMS[
                    "microservices_home"]),
                'hostname': 'example.org'}}
        check_code_message = \
            'Unexpected exit code. Expected {}.'.format(exit_code)\
            + "https://bugs.launchpad.net/fuel-ccp/+bug/1608981"

        show_step(1)
        res = ccpcluster.fetch(
            params=config_fetch,
            expected=[exit_code],
            error_info=check_code_message)

        show_step(2)
        assert re.search(
            err_message,
            "".join(res['stderr_str']), flags=re.MULTILINE) is not None

        show_step(3)
        assert 'Traceback' not in res['stderr_str'], (
            'traceback printed'
            'Defect https://bugs.launchpad.net/fuel-ccp/+bug/1608981')

        show_step(4)
        cmd_fetched = \
            ('ls -d1 {}/*'.format(
                settings.CCP_ENVIRONMENT_PARAMS["microservices_home"]))
        underlay.check_call(
            cmd_fetched, expected=[2],
            verbose=True,
            host=config.k8s.kube_host)

    def test_ccp_fetch_incorrect_schema(self, config, underlay, ccpcluster,
                                        show_step):
        """Fetch repo by incorrect schema using ccp tool
        Precondition:
        ccp config:
          repositories:
            path: $microservices-home
            fuel_ccp_debian_base: htt://example.org

        Scenario:
            1. exec ccp fetch with config
            2. Verify fatal: Unable to find remote helper for \'htt\'
            3. Verify no traceback printed for known negative case
            4. Verify that no repositories fetched
        """
        err_message = 'fatal: Unable to find remote helper for \'htt\''

        config_fetch = {
            'repositories': {
                'path': '{}'.format(settings.CCP_ENVIRONMENT_PARAMS[
                    "microservices_home"]),
                'fuel_ccp_debian_base': 'htt://example.org'}}

        show_step(1)
        res = ccpcluster.fetch(params=config_fetch)

        show_step(2)
        assert err_message in res['stderr_str']

        show_step(3)
        assert 'Traceback' not in res['stderr_str'], (
            'traceback printed '
            'Defect https://bugs.launchpad.net/fuel-ccp/+bug/1620361')

        show_step(4)
        cmd_fetched = \
            ('ls -d1 {}/fuel-ccp-debian-base'
             .format(settings.CCP_ENVIRONMENT_PARAMS["microservices_home"]))
        underlay.check_call(
            cmd_fetched, expected=[2],
            verbose=True,
            host=config.k8s.kube_host)
