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

DEFAULT_REPOS = ['fuel-ccp-debian-base',
                 'fuel-ccp-entrypoint',
                 'fuel-ccp-etcd',
                 'fuel-ccp-glance',
                 'fuel-ccp-heat',
                 'fuel-ccp-horizon',
                 'fuel-ccp-keystone',
                 'fuel-ccp-mariadb',
                 'fuel-ccp-memcached',
                 'fuel-ccp-neutron',
                 'fuel-ccp-nova',
                 'fuel-ccp-openstack-base',
                 'fuel-ccp-rabbitmq',
                 'fuel-ccp-stacklight']


@pytest.fixture(scope='function')
def git_mock(config, underlay):
    '''
    Instantiate a mock ssh git server. Server host repositories in the /git
     project. Git project mounted to /docker_data/openstack on host machine
    Setup password-less access to repo for vagrant user from kube_host
    Populate with default openstack repositories
    '''
    cmd_git_setup = 'git clone https://github.com/unixtastic/git-ssh-server ' \
                    '&& cd git-ssh-server ' \
                    '&& docker build -t \'unixtastic/git-ssh-server\' . ' \
                    '&& docker run -d -p 2222:22 ' \
                    '-v /docker_data/openstack:/git unixtastic/git-ssh-server'
    logger.info("Instantiating ssh-git-server mock instance")
    ssh_server_docker_container_id = underlay.sudo_check_call(
        cmd_git_setup,
        host=config.k8s.kube_host)['stdout'][-1].strip()
    logger.info("Started ssh-git-server in {} container".format(
        ssh_server_docker_container_id))

    cmd_config_permitions = 'cat ~/.ssh/id_rsa_vagrant >> ~/.ssh/id_rsa'
    cmd_config_permitions_sudo = \
        ['cd /docker_data/openstack',
         'mkdir /docker_data/openstack/.ssh',
         'chown -R 987:987 /docker_data/openstack/.ssh',
         'chmod -R 700 /docker_data/openstack/.ssh',
         'touch /docker_data/openstack/.ssh/authorized_keys',
         'chmod 600 /docker_data/openstack/.ssh/authorized_keys',
         'chown 987:987 /docker_data/openstack/.ssh/authorized_keys',
         'cat ~/.ssh/id_rsa_vagrant.pub >> '
         '/docker_data/openstack/.ssh/authorized_keys',
         'chmod 600 ~/.ssh/id_rsa',
         'touch /docker_data/openstack/.hushlogin',
         'docker exec {} sed -i \'$ a {}\' /etc/ssh/sshd_config'.format(
             ssh_server_docker_container_id,
             'AuthorizedKeysFile      /git/.ssh/authorized_keys'),
         'sed -i \'$ a {}\' /etc/ssh/ssh_config'.format(
             'StrictHostKeyChecking no'),
         'docker exec {} /etc/init.d/ssh restart'.format(
             ssh_server_docker_container_id)
         ]
    logger.info("Configuring public keys and permissions...")
    underlay.check_call(cmd_config_permitions,
                        host=config.k8s.kube_host, expected=[0])
    for cmd in cmd_config_permitions_sudo:
        underlay.sudo_check_call(cmd,
                                 host=config.k8s.kube_host, expected=[0])

    logger.info("Configuring public keys and permissions completed")

    logger.info("Cloning all default repos from openstack public repo")
    for repo in DEFAULT_REPOS:
        logger.info('Cloning {}...'.format(repo))
        underlay.sudo_check_call(
            'git clone --mirror https://review.openstack.org:443/openstack/{}'
            ' /docker_data/openstack/{}'.format(
                repo, repo), host=config.k8s.kube_host, expected=[0])
        underlay.sudo_check_call(
            'cd /docker_data/openstack/{} && chown -R 987:987 .'.format(repo),
            host=config.k8s.kube_host, expected=[0])


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
            ('ls -d1 ~/microservices-repos/* | xargs -n 1 basename')
        res = [s.strip() for s in underlay.check_call(
            cmd_fetched, expected=[0],
            verbose=True,
            host=config.k8s.kube_host)['stdout']]
        assert set(DEFAULT_REPOS) == set(res), \
            'Unexpected repo\'s downloaded' \
            ' Expected count {}, actual {}'.format(
                len(DEFAULT_REPOS), len(res))

    def test_ccp_fetch_some_via_ssh(self, config, underlay, ccpcluster,
                                    git_mock):
        """Test for ccp Fetch selected openstack repositories for master by ssh
         using fuel-ccp tool

        Scenario:
            1. exec ccp --repositories-protocol ssh '
             '--repositories-username vagrant --repositories-port 29418 '
             '--repositories-path $(pwd)/microservices-repos '
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
             '--repositories-path $(pwd)/microservices-repos '
             '--repositories-names fuel-ccp-debian-base,fuel-ccp-entrypoint '
             'fetch')
        underlay.check_call(cmd_fetch, expected=[0], verbose=True,
                            host=config.k8s.kube_host)
        cmd_fetched = \
            ('ls -d1 ~/microservices-repos/* | xargs -n 1 basename')
        res = [s.strip() for s in underlay.check_call(
            cmd_fetched, expected=[0],
            verbose=True,
            host=config.k8s.kube_host)['stdout']]
        assert set(expected) == set(res), 'Unexpected repo\'s downloaded' \
                                          ' Expected count {}, actual {}' \
            .format(len(expected), len(res))

        cmd_origin = "cd ~/microservices-repos/ &&" + \
                     "cd {} && ".format(expected[0]) + \
                     "git remote show origin | grep ssh://git@localhost:2222"
        assert underlay.check_call(cmd_origin, expected=[0], verbose=True,
                                   host=config.k8s.kube_host), \
            'Downloaded images are not from specified repository'

    def test_ccp_fetch_nonexisting_repo(self, config, underlay, ccpcluster):
        """Fetch nonexistent repo using fuel-ccp tool

        Scenario:
            1. exec ccp --repositories-path $(pwd)/microservices-repos '
             '--repositories-fuel-ccp-debian-base fuel-ccp-not-exist fetch
            2. Verify no traceback printed for known negative case
            3. Verify fatal: repository 'fuel-ccp-not-exist' not found"
            and exit code not 0
        """
        exit_code = 0
        err_message = 'fatal: repository \'http://example.org/\' not found'
        cmd_fetch = \
            ('ccp --repositories-path $(pwd)/microservices-repos '
             '--repositories-fuel-ccp-debian-base --repositories-hostname '
             'fuel-ccp-not-exist fetch')
        res = underlay.check_call(cmd_fetch, verbose=True,
                                  host=config.k8s.kube_host,
                                  raise_on_err=False)

        assert res['exit_code'] != exit_code, \
            'Wrong exit code: actual {} expected {}'.format(
                res['exit_code'], exit_code)
        assert err_message in res['stderr_str']
        assert 'Traceback' not in res['stderr_str'], (
            'traceback printed'
            'Defect https://bugs.launchpad.net/fuel-ccp/+bug/1620354')
        cmd_fetched = \
            ('ls -d1 ~/microservices-repos/* | xargs -n 1 basename')
        res = [s.strip() for s in underlay.check_call(
            cmd_fetched, expected=[0],
            verbose=True,
            host=config.k8s.kube_host, raise_on_err=False)['stdout']]
        assert len(res) == 0, \
            'Unexpected repo\'s downloaded' \
            'Defect https://bugs.launchpad.net/fuel-ccp/+bug/1620354'

    def test_ccp_fetch_incorrect_url(self, config, underlay, ccpcluster):
        """Fetch repo by incorrect url using ccp tool

        Scenario:
            1. exec ccp --repositories-path $(pwd)/microservices-repos
            --repositories-names --repositories-names http://example.org/ fetch
            2. Verify no traceback printed for known negative case
            3. Verify fatal: repository 'http://example.org/' not found"
            and exit code not 0
        """
        exit_code = 0
        err_message = 'Failed to fetch: ' \
                      'no such option fuel_ccp_not_exist in group'
        cmd_fetch = \
            ('ccp --repositories-path $(pwd)/microservices-repos '
             '--repositories-names http://example.org/ fetch')
        res = underlay.check_call(cmd_fetch, verbose=True,
                                  host=config.k8s.kube_host,
                                  raise_on_err=False)

        assert res['exit_code'] != exit_code, \
            'Wrong exit code: actual {} expected {}'.format(
                res['exit_code'], exit_code)
        assert err_message in res['stderr_str']
        assert 'Traceback' not in res['stderr_str'], (
            'traceback printed'
            'Defect https://bugs.launchpad.net/fuel-ccp/+bug/1608981')
        cmd_fetched = \
            ('ls -d1 ~/microservices-repos/* | xargs -n 1 basename')
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
            1. exec ccp --repositories-path $(pwd)/microservices-repos '
             '--repositories-fuel-ccp-debian-base htt://example.org fetch
            2. Verify no traceback printed for known negative case
            3. Verify fatal: Unable to find remote helper for \'htt\'
        """
        exit_code = 0
        err_message = 'fatal: Unable to find remote helper for \'htt\''
        cmd_fetch = \
            ('ccp --repositories-path $(pwd)/microservices-repos '
             '--repositories-fuel-ccp-debian-base htt://example.org fetch')
        res = underlay.check_call(cmd_fetch, verbose=True,
                                  host=config.k8s.kube_host,
                                  raise_on_err=False)

        assert res['exit_code'] != exit_code,\
            'Wrong exit code: actual {} expected {}'\
                .format(res['exit_code'], exit_code)
        assert err_message in res['stderr_str']
        assert 'Traceback' not in res['stderr_str'], (
            'traceback printed '
            'Defect https://bugs.launchpad.net/fuel-ccp/+bug/1620361')
        cmd_fetched = \
            ('ls -d1 ~/microservices-repos/* | xargs -n 1 basename')
        res = [s.strip() for s in underlay.check_call(
            cmd_fetched, expected=[0],
            verbose=True,
            host=config.k8s.kube_host, raise_on_err=False)['stdout']]
        assert len(res) == (len(DEFAULT_REPOS) - 1), \
            'Unexpected repo\'s downloaded' \
            'Defect https://bugs.launchpad.net/fuel-ccp/+bug/1620361'
