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

pytest_plugins = ['mcp_tests.system_tests.common_fixtures',
                  'mcp_tests.system_tests.config_fixtures',
                  'mcp_tests.system_tests.underlay_fixtures',
                  'mcp_tests.system_tests.k8s_fixtures',
                  'mcp_tests.system_tests.ccp_fixtures',]
