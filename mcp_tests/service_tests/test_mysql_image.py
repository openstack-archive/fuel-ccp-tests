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

import pytest
import traceback

from mcp_tests.helpers import mcp_tests_exceptions
from mcp_tests.logger import logger
from mcp_tests import settings


class TestMysqlImage(object):
    """Test class consits simple tests for mysql container"""

    @pytest.mark.mysql_base
    def test_mysql_is_running(self):
        """Start container from image, check if mysql is running

        Scenario:
            1. Get image from private registry
            2. Start container with it
            3. Check if mysql is running
            4. Destroy container

        """
        logger.info('Check  if registry set {0}'.format(
            settings.PRIVATE_REGISTRY))
        try:
            if not settings.PRIVATE_REGISTRY:
                raise mcp_tests_exceptions.VariableNotSet(
                    settings.PRIVATE_REGISTRY, 'localhost:5002/registry')
        except mcp_tests_exceptions.VariableNotSet:
            logger.error(traceback.format_exc())
