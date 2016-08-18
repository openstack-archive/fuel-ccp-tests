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

from mcp_tests.managers import ccp
from mcp_tests.managers import k8s
from mcp_tests import settings


@pytest.fixture(scope='session')
def env_with_k8s_and_ccp(env, env_with_k8s):
    """Fixture to install fuel-ccp on k8s environment

    :param env_with_k8s: envmanager.EnvironmentManager
    """
    ccp.CCPManager.install_ccp(env)


@pytest.fixture(scope='function')
def k8s_installed(request, env):
    """Fixture to prepare needed state and revert from snapshot if it's needed

    To install k8s on top of env with default settings, test class should has
    kube_settings variable with None or empty dict value. If there are no that
    attribute, DEFAULT_CUSTOM_YAML, compiled in settings, will be used.

    Value of module variable INSTALL_ACTION is used to get required method of
    test class to perform k8s deployment.

    :param request: pytest.python.FixtureRequest
    :param env: envmanager.EnvironmentManager
    """
    kube_settings = getattr(request.instance, 'kube_settings',
                            settings.DEFAULT_CUSTOM_YAML)
    k8s.K8SManager.install_k8s(env, custom_yaml=kube_settings)
