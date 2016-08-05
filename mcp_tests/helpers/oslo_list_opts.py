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

from mcp_tests.helpers import oslo_cfg_types as ct


def list_opts():
    """Return a list of oslo.config options available in the fuel-ccp-tests.
    """
    # TODO(ddmitriev): discovery oslo_config options from tests and serialize
    # to list of tuples.
    return ()

