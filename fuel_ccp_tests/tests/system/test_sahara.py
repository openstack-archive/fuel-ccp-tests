
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

import base_test
from fuel_ccp_tests import logger

LOG = logger.logger


class TestSahara(base_test.SystemBaseTest):
    """ Sahara deploy method

    """
    @pytest.mark.fail_snapshot
    @pytest.mark.sahara
    def test_sahara_deploy(self, underlay, show_step, sahara_deployed):
        """Deploy sahara

        Scenario:
        1. Revert snapshot with deployed sahara

        Duration 5 min
        """
        show_step(1)
        sahara_node = underlay.node_names()[1]
        sahara_node_ip = underlay.host_by_node_name(sahara_node)
        assert sahara_node_ip is None
