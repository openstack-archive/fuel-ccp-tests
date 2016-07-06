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

import logging

import pytest

from mcp_tests.helpers import mcp_tests_exceptions as exc
from mcp_tests import logger
from mcp_tests import settings

logging.getLogger('EnvironmentManager').addHandler(logger.console)

LOG = logger.logger


class SystemBaseTest(object):
    """SystemBaseTest contains setup/teardown for environment creation"""

    @classmethod
    def setup_class(cls):
        """Create Environment or use an existing one"""
        LOG.info('Trying to get existing environment')
        try:
            cls.env.get_env_by_name(name=settings.ENV_NAME)
        except exc.EnvironmentDoesNotExist:
            LOG.info("Environment doesn't exist, creating new one")
            cls.env.create_environment()
            LOG.info("Environment created")

    @pytest.mark.skipif(not settings.SUSPEND_ENV_ON_TEARDOWN,
                        reason="Suspend isn't needed"
                        )
    @classmethod
    def teardown_class(cls):
        """Suspend environment"""
        LOG.info("Suspending environment")
        cls.env.suspend()
