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

import re

from fuel_ccp_tests import logger


LOG = logger.logger


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
                                ' ',         # line breaks by single space
                                doc_match.group('title')
                                ).strip()

    test_case['steps'] = []
    for raw_step in re.split(r'\s+\d+\.\s*', doc_match.group('scenario')):
        if not raw_step:
            # start or end of the string
            continue
        test_case['steps'].append(
            re.sub(r'[\n\s]+',  # replace multiple spaces and
                   ' ',         # line breaks by single space
                   raw_step
                   ).strip()
        )

    # TODO(apanchenko): now it works only with 'seconds'
    duration = doc_match.group('duration') or 1000
    test_case['duration'] = int(duration)
    return test_case


def log_step(func, step_num):
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
