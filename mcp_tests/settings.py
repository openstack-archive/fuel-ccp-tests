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


import os
import pkg_resources
import time

_boolean_states = {'1': True, 'yes': True, 'true': True, 'on': True,
                   '0': False, 'no': False, 'false': False, 'off': False}

_default_conf = pkg_resources.resource_filename(
    __name__, 'templates/default.yaml')
# _default_conf = os.getcwd() + '/mcp_tests/templates/default.yaml'


def get_var_as_bool(name, default):
    value = os.environ.get(name, '')
    return _boolean_states.get(value.lower(), default)

LOGS_DIR = os.environ.get('LOGS_DIR', os.getcwd())
TIMESTAT_PATH_YAML = os.environ.get(
    'TIMESTAT_PATH_YAML', os.path.join(
        LOGS_DIR, 'timestat_{}.yaml'.format(time.strftime("%Y%m%d"))))
SSH_NODE_CREDENTIALS = os.environ.get('SSH_NODE_CREDENTIALS',
                                      {'login': 'vagrant',
                                       'password': 'vagrant'})

ENV_NAME = os.environ.get('ENV_NAME', 'mcp_qa-test')
IMAGE_PATH = os.environ.get('IMAGE_PATH', None)
CONFIG_PATH = os.environ.get('CONF_PATH', os.path.abspath(_default_conf))
SUSPEND_ENV_ON_TEARDOWN = os.environ.get('SUSPEND_ENV_ON_TEARDOWN', True)
DEPLOY_SCRIPT = os.environ.get("DEPLOY_SCRIPT", None)

PRIVATE_REGISTRY = os.environ.get('PRIVATE_REGISTRY', None)

KUBE_ADMIN_USER = os.environ.get('KUBE_ADMIN_USER', 'root')
KUBE_ADMIN_PASS = os.environ.get('KUBE_ADMIN_PASS', 'changeme')
KUBE_HOST = os.environ.get('KUBE_HOST', None)
