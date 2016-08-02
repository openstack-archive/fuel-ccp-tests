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
    snapshot_name = extract_name_from_mark(revert_snapshot) or \
        INITIAL_SNAPSHOT_SUFFIX
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
        result.create_snapshot(INITIAL_SNAPSHOT_SUFFIX)
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
        if hasattr(request.node, 'rep_call') and request.node.rep_call.passed \
                and snapshot_needed:
            snapshot_name = extract_name_from_mark(snapshot_needed) or \
                "{}_passed".format(default_snapshot_name)
            env.create_snapshot(snapshot_name)

        elif hasattr(request.node, 'rep_setup') and \
                request.node.rep_setup.failed and fail_snapshot:
            snapshot_name = "{0}_prep_failed".format(default_snapshot_name)
            env.create_snapshot(snapshot_name)

        elif hasattr(request.node, 'rep_call') and \
                request.node.rep_call.failed and fail_snapshot:
            snapshot_name = "{0}_failed".format(default_snapshot_name)
            env.create_snapshot(snapshot_name)
    request.addfinalizer(test_fin)
