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

from mcp_tests import logger
from mcp_tests.managers import envmanager_devops
from mcp_tests.managers import envmanager_empty
from mcp_tests.managers import underlay_ssh_manager

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
def hardware(config):
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
