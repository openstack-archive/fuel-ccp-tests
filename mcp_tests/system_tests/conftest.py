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
from __future__ import division
import time

import pytest
from devops import error

from mcp_tests import logger
from mcp_tests import settings
from mcp_tests.managers import envmanager
from mcp_tests.models.k8s import cluster

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


@pytest.fixture(scope='session')
def k8sclient(env):
    """Fixture to get K8sCluster instance for session

    :param env: envmanager.EnvironmentManager
    :rtype: cluster.K8sCluster
    """
    admin_ip = env.node_ip(env.k8s_nodes[0])
    k8s = cluster.K8sCluster(user=settings.KUBE_ADMIN_USER,
                             password=settings.KUBE_ADMIN_PASS,
                             host=admin_ip)
    return k8s


@pytest.fixture(scope='function')
def snapshot_name(request, env):
    """Fixture to get snapshot_name

    Marks:
        revert_snapshot - if used this mark with 'name' parameter,
        use given name as result

    :param request: pytest.python.FixtureRequest
    :param env: envmanager.EnvironmentManager
    :rtype: string
    """
    revert_snapshot = request.keywords.get('revert_snapshot', None)
    snapshot_name = make_snapshot_name(
        env, extract_name_from_mark(revert_snapshot), INITIAL_SNAPSHOT_SUFFIX)
    return snapshot_name


@pytest.fixture(scope='function', autouse=True)
def revert_snapshot(request, env, snapshot_name):
    """Fixture to revert environment to snapshot

    :param request: pytest.python.FixtureRequest
    :param env: envmanager.EnvironmentManager
    :param snapshot_name: string
    """
    if snapshot_name:
        if env.has_snapshot(snapshot_name):
            print("Reverting snapshot {0}".format(snapshot_name))
            env.revert_snapshot(snapshot_name)
        else:
            pytest.fail("Environment doesn't have snapshot named '{}'".format(
                snapshot_name))


@pytest.fixture(scope='function',
                params=[False, True],
                ids=["using_defaults", "with_custom_yaml"])
def kargo_deploy(request, env):
    """Fixture to prepare needed state and revert from snapshot if it's needed

    :param request: pytest.python.FixtureRequest
    :param env: envmanager.EnvironmentManager
    """
    ACTION = "deploy_kargo"
    if getattr(request.instance, ACTION) is None:
        pytest.fail(msg="Test instance hasn't attribute '{0}'".format(
            ACTION
        ))
    custom_yaml = request.param
    request.instance.deploy_kargo(env,
                                  use_custom_yaml=custom_yaml)


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
        if request.node.rep_call.passed:
            if snapshot_needed:
                snapshot_name = make_snapshot_name(
                    env, extract_name_from_mark(snapshot_needed),
                    env.d_env_name + "_" + request.node.function.__name__ +
                    "_passed"
                )
                request.instance.create_env_snapshot(
                    name=snapshot_name, env=env
                )
        elif request.node.rep_setup.failed:
            if fail_snapshot:
                suffix = "{0}_prep_failed".format(
                    request.node.function.__name__
                )
                request.instance.create_env_snapshot(
                    name=make_snapshot_name(
                        env, suffix, None
                    ), env=env
                )
        elif request.node.rep_call.failed:
            if fail_snapshot:
                suffix = "{0}_failed".format(
                    request.node.function.__name__
                )
                snapshot_name = make_snapshot_name(
                    env, suffix, None
                )
                request.instance.create_env_snapshot(
                    name=snapshot_name, env=env
                )
    request.addfinalizer(test_fin)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)


def pytest_runtest_setup(item):
    item.cls._current_test = item.function
    item._start_time = time.time()
    head = "<" * 5 + "#" * 30 + "[ {} ]" + "#" * 30 + ">" * 5
    head = head.format(item.function.__name__)
    start_step = "\n{head}".format(head=head)
    LOG.info(start_step)


def pytest_runtest_teardown(item):
    step_name = item.function.__name__
    if hasattr(item, '_start_time'):
        spent_time = time.time() - item._start_time
    else:
        spent_time = 0
    minutes = spent_time // 60
    seconds = int(round(spent_time)) % 60
    finish_step = "FINISH {} TEST. TOOK {} min {} sec".format(
        step_name, minutes, seconds
    )
    foot = "\n" + "<" * 5 + "#" * 30 + "[ {} ]" + "#" * 30 + ">" * 5
    foot = foot.format(finish_step)
    LOG.info(foot)
