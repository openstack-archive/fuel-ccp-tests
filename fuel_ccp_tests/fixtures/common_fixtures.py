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
import re
import time

import pytest

from fuel_ccp_tests import logger
from fuel_ccp_tests.helpers import utils

LOG = logger.logger


@pytest.yield_fixture(scope='session')
def ssh_keys_dir(request):
    ssh_keys_dir = utils.generate_keys()
    LOG.info("SSH keys were generated in {}".format(ssh_keys_dir))
    yield ssh_keys_dir
    utils.clean_dir(ssh_keys_dir)
    LOG.info("Tmp dir {} with generated ssh keys was cleaned".format(
        ssh_keys_dir))


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)


def pytest_runtest_setup(item):
    if item.cls is not None:
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


def parse_test_doc(docstring):
    test_case = {}
    parse_regex = re.compile(r'(?P<title>^(.*\S.*\n)+)+'
                             r'(?P<empty_line1>\s*\n)'
                             r'\s*Scenario:\s*\n(?P<scenario>(.+\n)+)'
                             r'(?P<empty_line2>\s*(\n|$))?'
                             r'(\s*Duration:\s+(?P<duration>\d+).*\n)?')
    doc_match = re.match(parse_regex, docstring)

    if not doc_match:
        LOG.error("Can't parse test docstring, unknown format!")
        return test_case

    test_case['title'] = re.sub(r'[\n\s]+',  # replace multiple spaces and
                                ' ',  # line breaks by single space
                                doc_match.group('title')
                                ).strip()

    test_case['steps'] = []
    for raw_step in re.split(r'\s+\d+\.\s*', doc_match.group('scenario')):
        if not raw_step:
            # start or end of the string
            continue
        test_case['steps'].append(
            re.sub(r'[\n\s]+',  # replace multiple spaces and
                   ' ',  # line breaks by single space
                   raw_step
                   ).strip()
        )

    # TODO(apanchenko): now it works only with 'seconds'
    duration = doc_match.group('duration') or 1000
    test_case['duration'] = int(duration)
    return test_case


def show_step(func, step_num):
    if not func.__doc__:
        LOG.error("Can't show step #{0}: docstring for method {1} not "
                  "found!".format(step_num, func.__name__))
    test_case_steps = parse_test_doc(func.__doc__)['steps']
    try:
        LOG.info(" *** [STEP#{0}] {1} ***".format(
            step_num,
            test_case_steps[step_num - 1]))
    except IndexError:
        LOG.error("Can't show step #{0}: docstring for method {1} does't "
                  "contain it!".format(step_num, func.__name__))


@pytest.fixture(scope='function')
def log_helper(request):
    class LogHelper(object):
        def __init__(self, show_step_func):
            self._show_step_func = show_step_func
            self.test_func = request.function

        def show_step(self, step_number):
            self._show_step_func(self.test_func, step_number)

    return LogHelper(show_step_func=show_step)
