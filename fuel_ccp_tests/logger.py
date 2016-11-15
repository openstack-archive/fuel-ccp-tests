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
import functools
import logging
import os
import traceback

from fuel_ccp_tests import settings

if not os.path.exists(settings.LOGS_DIR):
    os.makedirs(settings.LOGS_DIR)

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s %(filename)s:'
                    '%(lineno)d -- %(message)s',
                    filename=os.path.join(settings.LOGS_DIR, 'tests.log'),
                    filemode='w')

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s %(filename)s:'
                              '%(lineno)d -- %(message)s')
console.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.addHandler(console)


# suppress iso8601 and paramiko debug logging
class NoDebugMessageFilter(logging.Filter):
    def filter(self, record):
        return not record.levelno <= logging.DEBUG


logging.getLogger('paramiko.transport').addFilter(NoDebugMessageFilter())
logging.getLogger('paramiko.hostkeys').addFilter(NoDebugMessageFilter())
logging.getLogger('iso8601.iso8601').addFilter(NoDebugMessageFilter())


def debug(logger):
    def wrapper(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            logger.debug(
                "Calling: {} with args: {} {}".format(
                    func.__name__, args, kwargs
                )
            )
            try:
                result = func(*args, **kwargs)
                logger.debug(
                    "Done: {} with result: {}".format(func.__name__, result))
            except BaseException as e:
                logger.error(
                    '{func} raised: {exc!r}\n'
                    'Traceback: {tb!s}'.format(
                        func=func.__name__, exc=e, tb=traceback.format_exc()))
                raise
            return result
        return wrapped
    return wrapper


logwrap = debug(logger)
