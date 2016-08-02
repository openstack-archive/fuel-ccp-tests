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
import time

import pytest

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

       Input data:
           config.hardware.manager: one of ('devops', 'maas', None)
           config.hardware.config: path to the config file for the manager
           ...
           (additional variables for the hardware manager)

       Output data:
           config.status_name = Latest created or reverted snapshot name
           config.underlay.ssh = JSONList of SSH access credentials for nodes.
                                 This list will be used for initialization the
                                 model UnderlaySSHManager, see it for details.

       :rtype EnvironmentModel: if config.hardware.manager == 'devops'
       :rtype NoneType: if config.hardware.manager == None
    """
    env = None

    manager = config.hardware.manager

    if manager is None:
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

    def fin():
        if settings.SHUTDOWN_ENV_ON_TEARDOWN:
            LOG.info("Shutdown environment...")
            env.stop()

    request.addfinalizer(fin)
    return env


@pytest.fixture(scope='function', autouse=True)
def revert_snapshot(request, hardware):
    """Fixture to revert environment to snapshot

    Marks:
        revert_snapshot - if used this mark with 'name' parameter,
        use given name as result

    :param request: pytest.python.FixtureRequest
    :param env: envmanager.EnvironmentManager
    """
    revert_snapshot = request.keywords.get('revert_snapshot', None)
    snapshot_name = extract_name_from_mark(revert_snapshot)
    if revert_snapshot and snapshot_name:
        if hardware.has_snapshot(snapshot_name):
            LOG.info("Reverting snapshot {0}".format(snapshot_name))
            hardware.revert_snapshot(snapshot_name)
        else:
            if revert_snapshot.kwargs.get('strict', True):
                pytest.fail("Environment doesn't have snapshot "
                            "named '{}'".format(snapshot_name))


@pytest.fixture(scope='class')
def enable_lvm_support(underlay, hardware):
    def get_lvm_id(node):
        lvm = filter(lambda x: x.volume.name == 'lvm', node.disk_devices)[0]
        lvm_id = "{bus}-{serial}".format(
            bus=lvm.bus,
            serial=lvm.volume.serial[:20])
        LOG.info("Got lvm_id '{}' for node '{}'".format(lvm_id, node.name))
        return lvm_id

    def get_actions(lvm_id):
        return [
            "apt-get update",
            "apt-get install -y lvm2 liblvm2-dev thin-provisioning-tools",
            "systemctl enable lvm2-lvmetad.service",
            "systemctl enable lvm2-lvmetad.socket",
            "systemctl start lvm2-lvmetad.service",
            "systemctl start lvm2-lvmetad.socket",
            "pvcreate /dev/disk/by-id/{} && pvs".format(lvm_id),
            "vgcreate default /dev/disk/by-id/{} && vgs".format(lvm_id),
            "lvcreate -L 1G -T default/pool && lvs",
            "mkdir -p {}".format(settings.LVM_PLUGIN_DIR),
            "mv /tmp/{} {}".format(settings.LVM_FILENAME,
                                   settings.LVM_PLUGIN_DIR),
            "chmod +x {}/{}".format(settings.LVM_PLUGIN_DIR,
                                    settings.LVM_FILENAME)
        ]

    def get_remote(underlay, hardware):
        for node in hardware.k8s_nodes:
            LOG.info("Getting remote to node '{}'".format(node.name))
            remote = underlay.remote(
                host=hardware.node_ip(node))
            with remote.get_sudo(remote):
                yield remote, node
            LOG.info("Destroying remote to node '{}'".format(node.name))
            remote.close()

    lvm_snapshot = "lvm_support_enabled"
    if not hardware.has_snapshot(lvm_snapshot):
        LOG.info("Preparing environment for LVM usage")
        for remote, node in get_remote(underlay, hardware):
            LOG.info(
                "Uploading LVM plugin on remote node '{}'".format(node.name))
            remote.upload(settings.LVM_PLUGIN_PATH, '/tmp/')
            for cmd in get_actions(get_lvm_id(node)):
                LOG.info("Run command '{}' on node '{}'".format(
                    cmd, node.name
                ))
                restart = True
                while restart:
                    result = remote.check_call(command=cmd, expected=[0, 100])
                    if result['exit_code'] == 100:
                        LOG.debug(
                            "dpkg is locked on '{}' another "
                            "try in 5 secs".format(
                                node.name
                            ))
                        time.sleep(5)
                        restart = True
                    else:
                        restart = False
        LOG.info("Creating snapshot '{}'".format(lvm_snapshot))
        hardware.create_snapshot(lvm_snapshot)
    else:
        LOG.info("Snapshot '{}' found, trying to revert...".format(
            lvm_snapshot))
        hardware.revert_snapshot(lvm_snapshot)


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


@pytest.fixture(scope="session")
def underlay(config, hardware):
    """Fixture that should provide SSH access to underlay objects.

       Input data:
        - config.underlay.ssh : JSONList, *must* be provided, from 'hardware'
                                fixture or from an external config

    :rtype UnderlaySSHManager: Object that encapsulate SSH credentials;
                               - provide list of underlay nodes;
                               - provide SSH access to underlay nodes using
                                 node names or node IPs.
    """

    if not config.underlay.ssh:
        config.underlay.ssh = hardware.get_ssh_data()

    return underlay_ssh_manager.UnderlaySSHManager(config.underlay.ssh)
