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
from fuel_ccp_tests import logger
from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests.managers import ccpmanager
from fuel_ccp_tests import settings

LOG = logger.logger


@pytest.fixture(scope='function')
def ccp_actions(config, underlay):
    """Fixture that provides various actions for CCP

    :param config: fixture provides oslo.config
    :param underlay: fixture provides underlay manager
    :rtype: CCPManager

    For use in tests or fixtures to deploy a custom CCP
    """
    return ccpmanager.CCPManager(config, underlay)


@pytest.fixture(scope='function')
def ccpcluster(revert_snapshot, config, hardware,
               underlay, k8scluster, ccp_actions):
    """Fixture to get or install fuel-ccp on k8s environment

    :param config: fixture provides oslo.config
    :param hardware: fixture provides enviromnet manager
    :param underlay: fixture provides underlay manager
    :param k8scluster: fixture provides an installed k8s cluster
    :param ccp_actions: fixture provides CCPManager instance
    :rtype: CCPManager

    If config.ccp.os_host is not set, this fixture assumes that
    the ccp cluster was not deployed, and do the following:
    - deploy ccp cluster
    - make snapshot with name 'ccp_deployed'
    - (TODO)return CCPCluster instance, None at the moment

    If config.ccp.os_host was set, this fixture assumes that the ccp
    cluster was already deployed, and do the following:
    - (TODO)return CCPCluster instance, None at the moment

    If you want to revert 'ccp_deployed' snapshot, please use mark:
    @pytest.mark.revert_snapshot("ccp_deployed")
    """

    ccp_actions.default_params = settings.CCP_CLI_PARAMS

    # Try to guess environment config for reverted snapshot
    if revert_snapshot and config.ccp.os_host == '0.0.0.0':
        config.ccp.os_host = config.k8s.kube_host

    # Install CCP
    if config.ccp.os_host == '0.0.0.0':
        ccp_actions.install_ccp()
        ccp_actions.put_yaml_config(
            settings.CCP_CLI_PARAMS['deploy-config'],
            settings.CCP_DEFAULT_GLOBALS)
        ccp_actions.init_default_config()
        config.ccp.os_host = config.k8s.kube_host

        hardware.create_snapshot(ext.SNAPSHOT.ccp_deployed)

    else:
        # 1. hardware environment created and powered on
        # 2. config.underlay.ssh contains SSH access to provisioned nodes
        #    (can be passed from external config with TESTS_CONFIGS variable)
        # 3. config.k8s.* options contain access credentials to the already
        #    installed k8s API endpoint
        # 4. config.ccp.os_host contains an IP address of CCP admin node
        #    (not used yet)
        pass

    return ccp_actions


@pytest.fixture(scope='function')
def git_server_mock(config, underlay):
    '''
    Instantiate a mock ssh git server. Server host repositories in the /git
     project. Git project mounted to /docker_data/openstack on host machine
    Setup password-less access to repo for vagrant user from kube_host
    Populate with default openstack repositories
    '''
    cmd_git_setup = 'git clone https://github.com/unixtastic/git-ssh-server ' \
                    '&& cd git-ssh-server ' \
                    '&& docker build -t \'unixtastic/git-ssh-server\' . ' \
                    '&& docker run -d -p 2222:22 -p 3333:80 ' \
                    '-v /docker_data/openstack:/git unixtastic/git-ssh-server'
    LOG.info("Instantiating ssh-git-server mock instance")
    ssh_server_docker_container_id = underlay.sudo_check_call(
        cmd_git_setup,
        host=config.k8s.kube_host)['stdout'][-1].strip()
    LOG.info("Started ssh-git-server in {} container".format(
        ssh_server_docker_container_id))

    cmd_config_permisions = \
        'ssh-keygen -b 2048 -t rsa -f ~/.ssh/id_rsa_vagrant -q -N "" ' \
        '&& cat ~/.ssh/id_rsa_vagrant >> ~/.ssh/id_rsa'

    # Get git:git uid:git from container
    cmd_uid = 'id -u git'
    cmd_gid = 'id -u git'
    cmd_uid_docker = 'docker exec {} {}'.format(ssh_server_docker_container_id,
                                                cmd_uid)
    cmd_gid_docker = 'docker exec {} {}'.format(ssh_server_docker_container_id,
                                                cmd_gid)
    git_id = [underlay.sudo_check_call(cmd_uid_docker,
                                       host=config.k8s.kube_host,
                                       expected=[0])['stdout'][0].strip(),
              underlay.sudo_check_call(cmd_gid_docker,
                                       host=config.k8s.kube_host,
                                       expected=[0])['stdout'][0].strip()]

    cmd_config_permisions_sudo = \
        ['cd /docker_data/openstack',
         'mkdir /docker_data/openstack/.ssh',
         'chown -R {}:{} /docker_data/openstack/.ssh'.format(*git_id),
         'chmod -R 700 /docker_data/openstack/.ssh',
         'touch /docker_data/openstack/.ssh/authorized_keys',
         'chmod 600 /docker_data/openstack/.ssh/authorized_keys',
         'chown {}:{} /docker_data/openstack/.ssh/authorized_keys'.format(
             *git_id),
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
    LOG.info("Configuring public keys and permissions...")
    underlay.check_call(cmd_config_permisions,
                        host=config.k8s.kube_host, expected=[0])
    for cmd in cmd_config_permisions_sudo:
        underlay.sudo_check_call(cmd,
                                 host=config.k8s.kube_host, expected=[0])

    LOG.info("Configuring public keys and permissions completed")

    LOG.info("Cloning all default repos from openstack public repo")
    for repo in ext.DEFAULT_REPOS:
        LOG.info('Cloning {}...'.format(repo))
        underlay.sudo_check_call(
            'git clone --mirror https://review.openstack.org:443/openstack/{}'
            ' /docker_data/openstack/{}'.format(
                repo, repo), host=config.k8s.kube_host, expected=[0])
        underlay.sudo_check_call(
            'cd /docker_data/openstack/{} && chown -R {}:{} .'.format(
                repo, *git_id),
            host=config.k8s.kube_host, expected=[0])
