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


@pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
class TestCppFetch(object):
    """Check ccp fetch feature
    """
    def test_ccp_fetch_default(self, config, underlay, ccpcluster):
        """Test for ccp Fetch all openstack repositories for master by http
         using fuel-ccp tool

        Scenario:
            1. exec ccp --repositories-protocol http
            --repositories-port 80 fetch
            2. Verify that downloaded repos match to default repos list
        """
        cmd_fetch = \
            ('ccp --repositories-protocol http --repositories-port 80 fetch')
        underlay.check_call(cmd_fetch, expected=[0], verbose=True,
                            host=config.k8s.kube_host)
        cmd_fetched = \
            ('ls -d1 {}/* | xargs -n 1 basename'
             .format(settings.CCP_ENVIRONMENT_PARAMS["microservices_home"]))
        res = [s.strip() for s in underlay.check_call(
            cmd_fetched, expected=[0],
            verbose=True,
            host=config.k8s.kube_host)['stdout']]
        assert set(ext.DEFAULT_REPOS) == set(res), \
            'Unexpected repo\'s downloaded' \
            ' Expected count {}, actual {}'.format(
                len(ext.DEFAULT_REPOS), len(res))

    def test_ccp_fetch_some_via_ssh(self, config, underlay, ccpcluster,
                                    git_server_mock):
        """Test for ccp Fetch selected openstack repositories for master by ssh
         using fuel-ccp tool

        Scenario:
            1. exec ccp --repositories-protocol ssh '
             '--repositories-username git --repositories-port 2222 '
             '--repositories-host localhost '
             '--repositories-project git '
             '--repositories-path $(pwd)/ccp-repos '
             '--repositories-names fuel-ccp-debian-base,fuel-ccp-entrypoint '
             'fetch
            2. Verify that downloaded repos match to fuel-ccp-debian-base
            and  fuel-ccp-entrypointrepos list
            3. Verify that downloaded images from specified repository
        """
        expected = ['fuel-ccp-debian-base', 'fuel-ccp-entrypoint']
        cmd_fetch = \
            ('ccp --repositories-protocol ssh '
             '--repositories-username git --repositories-port 2222 '
             '--repositories-host localhost '
             '--repositories-project git '
             '--repositories-path $(pwd)/ccp-repos '
             '--repositories-names fuel-ccp-debian-base,fuel-ccp-entrypoint '
             'fetch')
        underlay.check_call(cmd_fetch, expected=[0], verbose=True,
                            host=config.k8s.kube_host)
        cmd_fetched = \
            ('ls -d1 {}/* | xargs -n 1 basename'
             .format(settings.CCP_ENVIRONMENT_PARAMS["microservices_home"]))
        res = [s.strip() for s in underlay.check_call(
            cmd_fetched, expected=[0],
            verbose=True,
            host=config.k8s.kube_host)['stdout']]
        assert set(expected) == set(res), 'Unexpected repo\'s downloaded' \
                                          ' Expected count {}, actual {}' \
            .format(len(expected), len(res))

        cmd_origin = (
            "cd {}/ &&".format(settings.CCP_ENVIRONMENT_PARAMS[
                "microservices_home"]) +
            "cd {} && ".format(expected[0]) +
            "git remote show origin | grep ssh://git@localhost:2222")
        assert underlay.check_call(cmd_origin, expected=[0], verbose=True,
                                   host=config.k8s.kube_host), \
            'Downloaded images are not from specified repository'

    def test_ccp_fetch_nonexisting_repo(self, config, underlay, ccpcluster):
        """Fetch nonexistent repo using fuel-ccp tool

        Scenario:
            1. exec ccp --repositories-path $(pwd)/ccp-repos '
             '--repositories-fuel-ccp-debian-base fuel-ccp-not-exist fetch
            2. Verify no traceback printed for known negative case
            3. Verify fatal: repository 'fuel-ccp-not-exist' not exists"
            and exit code not 0
        """
        exit_code = 1
        err_message = \
            'fatal: repository \'fuel-ccp-not-exist\' does not exist'
        cmd_fetch = \
            ('ccp --repositories-path $(pwd)/ccp-repos '
             '--repositories-fuel-ccp-debian-base fuel-ccp-not-exist fetch')
        res = underlay.check_call(cmd_fetch, verbose=True,
                                  host=config.k8s.kube_host,
                                  expected=[exit_code])

        assert err_message in res['stderr_str']
        assert 'Traceback' not in res['stderr_str'], (
            'traceback printed'
            'Defect https://bugs.launchpad.net/fuel-ccp/+bug/1620354')
        cmd_fetched = \
            ('ls -d1 {}/* | xargs -n 1 basename'
             .format(settings.CCP_ENVIRONMENT_PARAMS["microservices_home"]))
        error_info = '{} - directory exist, but should not'.format(
            settings.CCP_ENVIRONMENT_PARAMS["microservices_home"])

    def test_ccp_fetch_incorrect_url(self, config, underlay, ccpcluster):
        """Fetch repo by incorrect url using ccp tool

        Scenario:
            1. exec ccp --repositories-path $(pwd)/ccp-repos
            --repositories-hostname example.org fetch
            2. Verify no traceback printed for known negative case
            3. Verify fatal: repository 'http://example.org/' not found"
            and exit code not 0
        """
        exit_code = 1
        err_message = 'fatal: repository \'.*\' not found'
        cmd_fetch = \
            ('ccp --repositories-path $(pwd)/ccp-repos '
             '--repositories-hostname example.org fetch')
        res = underlay.check_call(cmd_fetch, verbose=True,
                                  host=config.k8s.kube_host,
                                  expected=[exit_code])

        assert re.search(
            err_message,
            "".join(res['stderr_str']), flags=re.MULTILINE) is not None
        assert 'Traceback' not in res['stderr_str'], (
            'traceback printed'
            'Defect https://bugs.launchpad.net/fuel-ccp/+bug/1608981')
        cmd_fetched = \
            ('ls -d1 {}/* | xargs -n 1 basename'.format(
                settings.CCP_ENVIRONMENT_PARAMS["microservices_home"]))
        res = [s.strip() for s in underlay.check_call(
            cmd_fetched, expected=[0],
            verbose=True,
            host=config.k8s.kube_host, raise_on_err=False)['stdout']]
        assert len(res) == 0, \
            'Unexpected repo\'s downloaded' \
            'Defect https://bugs.launchpad.net/fuel-ccp/+bug/1608981'

    def test_ccp_fetch_incorrect_schema(self, config, underlay, ccpcluster):
        """Fetch repo by incorrect schema using ccp tool

        Scenario:
            1. exec ccp --repositories-path $(pwd)/ccp-repos '
             '--repositories-fuel-ccp-debian-base htt://example.org fetch
            2. Verify no traceback printed for known negative case
            3. Verify fatal: Unable to find remote helper for \'htt\'
        """
        exit_code = 0
        err_message = 'fatal: Unable to find remote helper for \'htt\''
        cmd_fetch = \
            ('ccp --repositories-path $(pwd)/ccp-repos '
             '--repositories-fuel-ccp-debian-base htt://example.org fetch')
        res = underlay.check_call(cmd_fetch, verbose=True,
                                  host=config.k8s.kube_host,
                                  raise_on_err=False)

        assert res['exit_code'] != exit_code,\
            'Wrong exit code: actual {} expected {}'.format(
                res['exit_code'], exit_code)
        assert err_message in res['stderr_str']
        assert 'Traceback' not in res['stderr_str'], (
            'traceback printed '
            'Defect https://bugs.launchpad.net/fuel-ccp/+bug/1620361')
        cmd_fetched = \
            ('ls -d1 {}/* | xargs -n 1 basename'
             .format(settings.CCP_ENVIRONMENT_PARAMS["microservices_home"]))
        res = [s.strip() for s in underlay.check_call(
            cmd_fetched, expected=[0],
            verbose=True,
            host=config.k8s.kube_host, raise_on_err=False)['stdout']]
        assert len(res) == (len(ext.DEFAULT_REPOS) - 1), \
            'Unexpected repo\'s downloaded' \
            'Defect https://bugs.launchpad.net/fuel-ccp/+bug/1620361'
