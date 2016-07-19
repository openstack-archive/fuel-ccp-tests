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

PARAMS = [False, True]
IDS = ["default", "with_custom_yaml"]


@pytest.fixture(params=PARAMS, ids=IDS)
def use_custom_yaml(request):
    """Fixture for parametrize k8s deployment with or without custom yaml"""
    setattr(request.node.function, '_snapshot_name',
            "{0}_{1}".format(
                request.node.function.__name__,
                IDS[request.param_index])
            )
    return request.param


@pytest.fixture(scope='function')
def k8s_installed(request, env, use_custom_yaml):
    """Fixture to prepare needed state and revert from snapshot if it's needed

    :param request: pytest.python.FixtureRequest
    :param env: envmanager.EnvironmentManager
    :param use_custom_yaml: Bool
    """
    ACTION = "ccp_install_k8s"
    install_action = getattr(request.instance, ACTION, None)
    if install_action is None:
        pytest.fail(msg="Test instance hasn't attribute '{0}'".format(
            ACTION
        ))
    else:
        install_action(env,
                       use_custom_yaml=use_custom_yaml)
