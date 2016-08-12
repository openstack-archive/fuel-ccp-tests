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

SSH_LOGIN = os.environ.get('SSH_LOGIN', 'vagrant')
SSH_PASSWORD = os.environ.get('SSH_PASSWORD', 'vagrant')
SSH_NODE_CREDENTIALS = {"login": SSH_LOGIN,
                        "password": SSH_PASSWORD}

CONF_PATH = os.environ.get('CONF_PATH', os.path.abspath(_default_conf))
SUSPEND_ENV_ON_TEARDOWN = get_var_as_bool('SUSPEND_ENV_ON_TEARDOWN', True)
DEPLOY_SCRIPT = os.environ.get("DEPLOY_SCRIPT", None)

PRIVATE_REGISTRY = os.environ.get('PRIVATE_REGISTRY', None)

CCP_REPO = os.environ.get('CCP_REPO',
                          'https://github.com/openstack/fuel-ccp.git')

KARGO_REPO = os.environ.get('KARGO_REPO',
                            'https://github.com/kubespray/kargo.git')
KARGO_COMMIT = os.environ.get('KARGO_COMMIT', 'master')

KUBE_HOSTPATH_DYNAMIC_PROVISIONER = get_var_as_bool(
    'KUBE_HOSTPATH_DYNAMIC_PROVISIONER', True)
KUBE_ADMIN_USER = os.environ.get('KUBE_ADMIN_USER', 'root')
KUBE_ADMIN_PASS = os.environ.get('KUBE_ADMIN_PASS', 'changeme')
KUBE_HOST = os.environ.get('KUBE_HOST', None)
KUBE_VERSION = os.environ.get("KUBE_VERSION", "v1.3.0")
KUBE_NETWORK_PLUGIN = os.environ.get("KUBE_NETWORK_PLUGIN", "calico")
KUBE_PROXY_MODE = os.environ.get("KUBE_PROXY_MODE", "iptables")
HYPERKUBE_IMAGE_REPO = os.environ.get('HYPERKUBE_IMAGE_REPO',
                                      "quay.io/coreos/hyperkube")
HYPERKUBE_IMAGE_TAG = os.environ.get('HYPERKUBE_IMAGE_TAG',
                                     "{0}_coreos.0".format(KUBE_VERSION))
ETCD_DEPLOYMENT_TYPE = os.environ.get('ETCD_DEPLOYMENT_TYPE', "docker")
IPIP_USAGE = get_var_as_bool('IPIP_USAGE', True)


DEFAULT_CUSTOM_YAML = {
    "kube_network_plugin": KUBE_NETWORK_PLUGIN,
    "kube_proxy_mode": KUBE_PROXY_MODE,
    "kube_version": KUBE_VERSION,
    "hyperkube_image_repo": HYPERKUBE_IMAGE_REPO,
    "hyperkube_image_tag": HYPERKUBE_IMAGE_TAG,
    "etcd_deployment_type": ETCD_DEPLOYMENT_TYPE,
    # Configure calico to set --nat-outgoing and --ipip pool option 18
    "ipip": IPIP_USAGE
}
