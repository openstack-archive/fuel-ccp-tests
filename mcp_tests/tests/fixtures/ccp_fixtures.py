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

from mcp_tests.models.ccpmanager import CCPManager
#from mcp_tests import settings

#INSTALL_ACTION = "ccp_install_k8s"

@pytest.fixture(scope='session')
def ccpcluster(config, hardware, underlay, k8scluster):
    """Fixture to install fuel-ccp on k8s environment

    :param env: envmanager.EnvironmentManager
    """
#    CCPManager.install_ccp(env)
    CCPManager.install_ccp(underlay, k8scluster)
    # TODO: return OpenStack auth endpoint

@pytest.fixture(scope='session')
def ccp_actions(ccpcluster):
    """Fixture to install fuel-ccp on k8s environment

    :param env: envmanager.EnvironmentManager
    """
#    CCPManager.install_ccp(env)
    return CCPManager()
