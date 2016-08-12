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

from mcp_tests.managers.ccp import CCPManager
from mcp_tests import settings

INSTALL_ACTION = "ccp_install_k8s"

@pytest.fixture(scope='session')
def env_with_k8s_and_ccp(env, env_with_k8s):
    """Fixture to install fuel-ccp on k8s environment

    :param env_with_k8s: envmanager.EnvironmentManager
    """
    CCPManager.install_ccp(env)


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
    install_action = getattr(request.instance, INSTALL_ACTION, None)
    kube_settings = getattr(request.instance, 'kube_settings',
                            settings.DEFAULT_CUSTOM_YAML)
    if install_action is None:
        pytest.fail(msg="Test instance hasn't attribute '{0}'".format(
            INSTALL_ACTION
        ))
    else:
        install_action(env, custom_yaml=kube_settings)
