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

from mcp_tests import logger

LOG = logger.logger


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
