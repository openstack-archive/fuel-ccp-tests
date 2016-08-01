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


@pytest.fixture(scope='function')
def k8s_installed(request, env):
    """Fixture to prepare needed state and revert from snapshot if it's needed

    :param request: pytest.python.FixtureRequest
    :param env: envmanager.EnvironmentManager
    """
    ACTION = "ccp_install_k8s"
    install_action = getattr(request.instance, ACTION, None)
    kube_settings = getattr(request.instance, 'kube_settings', None)
    if install_action is None:
        pytest.fail(msg="Test instance hasn't attribute '{0}'".format(
            ACTION
        ))
    else:
        install_action(env, custom_yaml=kube_settings)
