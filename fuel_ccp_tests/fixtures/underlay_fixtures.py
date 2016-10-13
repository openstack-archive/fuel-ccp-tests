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
from datetime import datetime

from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.managers import envmanager_devops
from fuel_ccp_tests.managers import envmanager_empty
from fuel_ccp_tests.managers import underlay_ssh_manager

LOG = logger.logger


def extract_name_from_mark(mark):
    """Simple function to extract name from mark

    :param mark: pytest.mark.MarkInfo
    :rtype: string or None
    """
    if mark:
        if len(mark.args) > 0:
            return mark.args[0]
        elif 'name' in mark.kwargs:
            return mark.kwargs['name']
    return None


@pytest.fixture(scope="session")
def hardware(request, config):
    """Fixture for manage the hardware layer.

       - start/stop/reboot libvirt/IPMI(/MaaS?) nodes
       - snapshot/revert libvirt nodes (fuel-devops only)
       - block/unblock libvirt  networks/interfaces (fuel-devops only)

       This fixture should get a hardware configuration from
       'config' object or create a virtual/baremetal underlay
       using EnvironmentManager.

       Creates a snapshot 'hardware' with ready-to-use virtual environment
       (Only for config.hardware.manager='devops'):
        - just created virtual nodes in power-on state
        - node volumes filled with necessary content
        - node network interfaces connected to necessary devices

       config.hardware.manager: one of ('devops', 'maas', None)
       config.hardware.config: path to the config file for the manager
       config.hardware.current_snapshot = Latest created or reverted snapshot

       :rtype EnvironmentModel: if config.hardware.manager == 'devops'
       :rtype EnvironmentManagerEmpty: if config.hardware.manager == 'empty'
    """
    env = None

    manager = config.hardware.manager

    if manager == 'empty':
        # No environment manager is used.
        # 'config' should contain config.underlay.ssh settings
        # 'config' should contain config.underlay.current_snapshot setting
        env = envmanager_empty.EnvironmentManagerEmpty(config=config)

    elif manager == 'devops':
        # fuel-devops environment manager is used.
        # config.underlay.ssh settings can be empty or witn SSH to existing env
        # config.underlay.current_snapshot
        env = envmanager_devops.EnvironmentManager(config=config)
    else:
        raise Exception("Unknown hardware manager: '{}'".format(manager))

    # for devops manager: power on nodes and wait for SSH
    # for empty manager: do nothing
    # for maas manager: provision nodes and wait for SSH
    env.start()
    if not env.has_snapshot(ext.SNAPSHOT.hardware):
        env.create_snapshot(ext.SNAPSHOT.hardware)

    def fin():
        if settings.SHUTDOWN_ENV_ON_TEARDOWN:
            LOG.info("Shutdown environment...")
            env.stop()

    request.addfinalizer(fin)
    return env


@pytest.fixture(scope='function')
def revert_snapshot(request, hardware):
    """Revert snapshot for the test case

    Usage:
    @pytest.mark.revert_snapshot(name='<required_snapshot_name>')

    If the mark 'revert_snapshot' is absend, or <required_snapshot_name>
    not found, then an initial 'hardware' snapshot will be reverted.

    :rtype string: name of the reverted snapshot or None
    """
    revert_snapshot = request.keywords.get('revert_snapshot', None)
    snapshot_name = extract_name_from_mark(revert_snapshot)

    if snapshot_name and \
            hardware.has_snapshot(snapshot_name) and \
            hardware.has_snapshot_config(snapshot_name):
        hardware.revert_snapshot(snapshot_name)
        return snapshot_name
    else:
        hardware.revert_snapshot(ext.SNAPSHOT.hardware)
        return None


@pytest.fixture(scope='function', autouse=True)
def snapshot(request, hardware):
    """Fixture for creating snapshot at the end of test if it's needed

    Marks:
        snapshot_needed(name=None) - make snapshot if test is passed. If
        name argument provided, it will be used for creating snapshot,
        otherwise, test function name will be used

        fail_snapshot - make snapshot if test failed

    :param request: pytest.python.FixtureRequest
    :param env: envmanager.EnvironmentManager
    """
    snapshot_needed = request.keywords.get('snapshot_needed', None)
    fail_snapshot = request.keywords.get('fail_snapshot', None)

    def test_fin():
        default_snapshot_name = getattr(request.node.function,
                                        '_snapshot_name',
                                        request.node.function.__name__)
        if hasattr(request.node, 'rep_call') and request.node.rep_call.passed \
                and snapshot_needed:
            snapshot_name = extract_name_from_mark(snapshot_needed) or \
                "{}_passed".format(default_snapshot_name)
            hardware.create_snapshot(snapshot_name)

        elif hasattr(request.node, 'rep_setup') and \
                request.node.rep_setup.failed and fail_snapshot:
            snapshot_name = "{0}_prep_failed".format(default_snapshot_name)
            hardware.create_snapshot(snapshot_name)

        elif hasattr(request.node, 'rep_call') and \
                request.node.rep_call.failed and fail_snapshot:
            snapshot_name = "{0}_failed".format(default_snapshot_name)
            hardware.create_snapshot(snapshot_name)

    request.addfinalizer(test_fin)


@pytest.fixture(scope="function")
def underlay(revert_snapshot, config, hardware):
    """Fixture that should provide SSH access to underlay objects.

    - Starts the 'hardware' environment and creates 'underlay' with required
      configuration.
    - Fills the following object using the 'hardware' fixture:
      config.underlay.ssh = JSONList of SSH access credentials for nodes.
                            This list will be used for initialization the
                            model UnderlaySSHManager, see it for details.

    :rtype UnderlaySSHManager: Object that encapsulate SSH credentials;
                               - provide list of underlay nodes;
                               - provide SSH access to underlay nodes using
                                 node names or node IPs.
    """
    # If no snapshot was reverted, then try to revert the snapshot
    # that belongs to the fixture.
    # Note: keep fixtures in strict dependences from each other!
    if not revert_snapshot:
        if hardware.has_snapshot(ext.SNAPSHOT.underlay) and \
                hardware.has_snapshot_config(ext.SNAPSHOT.underlay):
            hardware.revert_snapshot(ext.SNAPSHOT.underlay)

    # Create Underlay
    if not config.underlay.ssh:
        # If config.underlay.ssh wasn't provided from external config, then
        # try to get necessary data from hardware manager (fuel-devops)
        config.underlay.ssh = hardware.get_ssh_data(
            roles=config.underlay.roles)

        underlay = underlay_ssh_manager.UnderlaySSHManager(config.underlay.ssh)

        if not config.underlay.lvm:
            underlay.enable_lvm(hardware.lvm_storages())
            config.underlay.lvm = underlay.config_lvm

        hardware.create_snapshot(ext.SNAPSHOT.underlay)

    else:
        # 1. hardware environment created and powered on
        # 2. config.underlay.ssh contains SSH access to provisioned nodes
        #    (can be passed from external config with TESTS_CONFIGS variable)
        underlay = underlay_ssh_manager.UnderlaySSHManager(config.underlay.ssh)

    return underlay


@pytest.fixture(scope='function', autouse=True)
def gather_logs(request, config, underlay):
    """Fixture executes Ansible command that gather logs from the K8s cluster
    nodes into a tarball and store results to the 'logs' directory.
    Logs collection starts if the test is failed.

    :param request: pytest.python.FixtureRequest
    :param config: fixture provides oslo.config
    :param underlay: fixture provides underlay manager
    """

    def test_fin():
        if hasattr(request.node, 'rep_call') and request.node.rep_call.failed:
            remote = underlay.remote(host=config.k8s.kube_host)
            cmd = "/usr/bin/ansible-playbook " \
                  "--ssh-extra-args '-o\ StrictHostKeyChecking=no' " \
                  "-u {user} -b " \
                  "--become-user=root -i workspace/inventory/inventory.cfg " \
                  "-e searchpath=workspace " \
                  "-e @workspace/utils/kargo/roles/configure_logs/defaults/" \
                  "main.yml " \
                  "workspace/kargo/scripts/collect-info.yaml".format(
                      user=settings.SSH_LOGIN)
            LOG.info(
                "Running command '{cmd}' on node {node_name}".format(
                    cmd=cmd,
                    node_name=remote.hostname
                )
            )
            remote.execute(cmd)
            tarball_name = 'logs.tar.gz'
            path_to_tarball = 'workspace/kargo/scripts/' + tarball_name
            tarball_prefix = request.node.function.__name__ + '_' + \
                datetime.now().strftime('%Y%m%d_%H%M%S') + '_'
            tarball_dst = settings.LOGS_DIR + '/logs/' + tarball_prefix + \
                tarball_name
            remote.download(path_to_tarball, tarball_dst)
            LOG.info("Logs are copied into: {}".format(tarball_dst))

    request.addfinalizer(test_fin)
