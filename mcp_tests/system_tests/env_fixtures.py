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


@pytest.fixture(scope='function')
def cluster_roles():
    """Store initial cluster roles

    :return: dict deploy_images_conf
    """
    deploy_images_conf = {
        'kubectl_label_nodes': {
            'openstack-compute-controller': [
                'node1',
                'node2',
                'node3',
            ],
            'openstack-controller': [
                'node1',
            ],
            'openstack-compute': [
                'node2',
                'node3',
            ]
        },
        'registry': settings.REGISTRY,
        'build_yaml': settings._build_conf,
        'path_to_log': settings.PATH_TO_LOG,
        'path_to_conf': settings.PATH_TO_CONF
    }
    return deploy_images_conf


@pytest.fixture(scope='class')
def prepare_env(env):
    """Fixture for installation microservices

    :param env: envmanager.EnvironmentManager
    :param master_node: self.env.k8s_ips[0]
    """
    remote = env.node_ssh_client(
        env.k8s_nodes[0],
        **settings.SSH_NODE_CREDENTIALS)
    for repo in settings.CCPINSTALLER, settings.MICROSERVICES:
        remote.upload(repo, '/home/vagrant')
    command = [
        'cd  ~/fuel-ccp && pip install .',
        '>{0}'.format(settings.PATH_TO_LOG),
        "cat ~/fuel-ccp/etc/topology-example.yaml >> /tmp/ccp-globals.yaml"
    ]
    with remote.get_sudo(remote):
        for cmd in command:
            LOG.info(
                "Running command '{cmd}' on node {node_name}".format(
                    cmd=cmd,
                    node_name=env.k8s_nodes[0].name
                )
            )
            result = remote.execute(cmd)
            assert result['exit_code'] == 0
        remote.close()
