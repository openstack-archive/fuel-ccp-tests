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


def make_snapshot_name(request, suffix, default):
    """Creating snapshot name

    :param request: pytest.python.FixtureRequest
    :param suffix: string
    :param default: string or None
    :rtype: string or None
    """
    if request:
        if suffix:
            return "{0}_{1}".format(
                request.instance.env.d_env_name,
                suffix
            )
    return default


@pytest.fixture(scope='function', autouse=True)
def prepare(request):
    """Fixture to prepare needed state and revert from snapshot if it's needed

    Marks:
        deploy_kargo(use_custom_yaml=False) - perform deploy_kargo action.

        revert_snapshot(name=NAME) - revert from snapshot with name <NAME>

    :param request: pytest.python.FixtureRequest
    """
    ACTION = "deploy_kargo"
    revert_snapshot = request.keywords.get('revert_snapshot', None)
    snapshot_name = make_snapshot_name(
        request, extract_name_from_mark(revert_snapshot), None)
    if snapshot_name:
        if request.instance.env.has_snapshot(snapshot_name):
            print("Reverting snapshot {0}".format(snapshot_name))
            request.instance.env.revert_snapshot(snapshot_name)
        elif revert_snapshot.kwargs.get('strict', False):
            pytest.fail(
                msg="Environment '{0}' hasn't snapshot named '{1}'".format(
                    request.instance.env.d_env_name,
                    snapshot_name
                ))
    deploy_kargo = request.keywords.get(ACTION, None)
    if deploy_kargo:
        if getattr(request.instance, ACTION) is None:
            pytest.fail(msg="Test instance hasn't attribute '{0}'".format(
                ACTION
            ))
        request.instance.deploy_kargo(
            use_custom_yaml=deploy_kargo.kwargs.get('use_custom_yaml', False))


@pytest.fixture(scope="class", autouse=True)
def environment(request):
    """Class fixture to get or create environment

    :param request: pytest.python.FixtureRequest
    """
    env = envmanager.EnvironmentManager(config_file=settings.CONF_PATH)
    snapshot_suffix = request.cls.initial_snapshot
    env_name = env.d_env_name
    initial_snapshot_name = "{0}_{1}".format(
        env_name,
        snapshot_suffix
    )
    try:
        env.get_env_by_name(env_name)
    except error.DevopsObjNotFound:
        LOG.info("Environment doesn't exist, creating a new one")
        env.create_environment()
        env.create_snapshot(initial_snapshot_name)
        LOG.info("Environment created")
    request.cls.env = env


@pytest.fixture(scope='function', autouse=True)
def snapshot(request):
    """Fixture for creating snapshot at the end of test if it's needed

    Marks:
        snapshot_needed(name=None) - make snapshot if test is passed. If
        name argument provided, it will be used for creating snapshot

        fail_snapshot - make snapshot if test failed

    :param request: pytest.python.FixtureRequest
    """
    snapshot_needed = request.keywords.get('snapshot_needed', None)
    fail_snapshot = request.keywords.get('fail_snapshot', None)

    def test_fin():
        if request.node.rep_call.passed:
            if snapshot_needed:
                snapshot_name = make_snapshot_name(
                    request, extract_name_from_mark(snapshot_needed),
                    request.node.function.__name__ + "_passed"
                )
                request.instance.create_env_snapshot(
                    name=snapshot_name
                )
        elif request.node.rep_setup.failed:
            if fail_snapshot:
                suffix = "{0}_prep_failed".format(
                    request.node.function.__name__
                )
                request.instance.create_env_snapshot(
                    name=make_snapshot_name(
                        request, suffix, None
                    )
                )
        elif request.node.rep_call.failed:
            if fail_snapshot:
                suffix = "{0}_failed".format(
                    request.node.function.__name__
                )
                snapshot_name = make_snapshot_name(
                    request, suffix, None
                )
                request.instance.create_env_snapshot(
                    name=snapshot_name
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
