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

from devops import error
import pytest

from mcp_tests import logger
from mcp_tests import settings
from mcp_tests.managers import envmanager


LOG = logger.logger
INITIAL_SNAPSHOT_SUFFIX = "initial"


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


def make_snapshot_name(env, suffix, default):
    """Creating snapshot name

    :param request: pytest.python.FixtureRequest
    :param suffix: string
    :param default: string or None
    :rtype: string or None
    """
    if env:
        if suffix:
            return "{0}_{1}".format(
                env.d_env_name,
                suffix
            )
        else:
            return "{0}_{1}".format(
                env.d_env_name,
                default
            )
    return default


@pytest.fixture(scope='function', autouse=True)
def revert_snapshot(request, env):
    """Fixture to revert environment to snapshot

    Marks:
        revert_snapshot - if used this mark with 'name' parameter,
        use given name as result

    :param request: pytest.python.FixtureRequest
    :param env: envmanager.EnvironmentManager
    """
    revert_snapshot = request.keywords.get('revert_snapshot', None)
    snapshot_name = make_snapshot_name(
        env, extract_name_from_mark(revert_snapshot), INITIAL_SNAPSHOT_SUFFIX)
    if revert_snapshot and snapshot_name:
        if env.has_snapshot(snapshot_name):
            LOG.info("Reverting snapshot {0}".format(snapshot_name))
            env.revert_snapshot(snapshot_name)
        else:
            pytest.fail("Environment doesn't have snapshot named '{}'".format(
                snapshot_name))


@pytest.fixture(scope='class')
def env_lvm_support(env):
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
            "pvcreate /dev/disk/by-id/{}".format(lvm_id),
            "pvs",
            "vgcreate default /dev/disk/by-id/{}".format(lvm_id),
            "vgs",
            "lvcreate -L 1G -T default/pool",
            "lvs",
            "mkdir -p {}".format(settings.LVM_PLUGIN_DIR),
            "mv /tmp/{} {}".format(settings.LVM_FILENAME,
                                   settings.LVM_PLUGIN_DIR)
        ]

    def get_remote(env):
        for node in env.k8s_nodes:
            LOG.info("Getting remote to node '{}'".format(node.name))
            remote = env.node_ssh_client(
                node, **settings.SSH_NODE_CREDENTIALS)
            with remote.get_sudo(remote):
                yield remote, node
            LOG.info("Destroying remote to node '{}'".format(node.name))
            remote.close()

    LOG.info("Preparing environment for LVM usage")
    for remote, node in get_remote(env):
        LOG.info("Uploading LVM plugin on remote node '{}'".format(node.name))
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
                        "dpkg is locked on '{}' another try in 5 secs".format(
                            node.name
                        ))
                    time.sleep(5)
                    restart = True
                else:
                    restart = False


@pytest.fixture(scope="session")
def env():
    """Fixture to get EnvironmentManager instance for session

    :rtype: envmanager.EnvironmentManager
    """
    result = envmanager.EnvironmentManager(config_file=settings.CONF_PATH)
    try:
        result.get_env_by_name(result.d_env_name)
    except error.DevopsObjNotFound:
        LOG.info("Environment doesn't exist, creating a new one")
        result.create_environment()
        result.create_snapshot(make_snapshot_name(result,
                                                  INITIAL_SNAPSHOT_SUFFIX,
                                                  None))
        LOG.info("Environment created")
    return result


@pytest.fixture(scope='function', autouse=True)
def snapshot(request, env):
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
        if hasattr(request.node, 'rep_call') and request.node.rep_call.passed:
            if snapshot_needed:
                snapshot_name = make_snapshot_name(
                    env, extract_name_from_mark(snapshot_needed),
                    default_snapshot_name +
                    "_passed"
                )
                request.instance.create_env_snapshot(
                    name=snapshot_name, env=env
                )
        elif (hasattr(request.node, 'rep_setup') and
              request.node.rep_setup.failed):
            if fail_snapshot:
                suffix = "{0}_prep_failed".format(
                    default_snapshot_name
                )
                request.instance.create_env_snapshot(
                    name=make_snapshot_name(
                        env, suffix, None
                    ), env=env
                )
        elif (hasattr(request.node, 'rep_call') and
              request.node.rep_call.failed):
            if fail_snapshot:
                suffix = "{0}_failed".format(
                    default_snapshot_name
                )
                snapshot_name = make_snapshot_name(
                    env, suffix, None
                )
                request.instance.create_env_snapshot(
                    name=snapshot_name, env=env
                )
    request.addfinalizer(test_fin)
