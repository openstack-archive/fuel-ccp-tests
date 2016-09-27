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
SHUTDOWN_ENV_ON_TEARDOWN = get_var_as_bool('SHUTDOWN_ENV_ON_TEARDOWN', True)
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
KUBE_VERSION = os.environ.get("KUBE_VERSION", "v1.3.5")

KUBE_NETWORK_PLUGIN = os.environ.get("KUBE_NETWORK_PLUGIN", "calico")
KUBE_PROXY_MODE = os.environ.get("KUBE_PROXY_MODE", "iptables")
IPIP_USAGE = get_var_as_bool('IPIP_USAGE', True)
DOCKER_VERSION = float(os.environ.get("DOCKER_VERSION", "1.12"))

HYPERKUBE_IMAGE_REPO = os.environ.get('HYPERKUBE_IMAGE_REPO',
                                      "quay.io/coreos/hyperkube")
HYPERKUBE_IMAGE_TAG = os.environ.get('HYPERKUBE_IMAGE_TAG', "{}_coreos.0"
                                     .format(KUBE_VERSION))
ETCD_IMAGE_REPO = os.environ.get('ETCD_IMAGE_REPO', "quay.io/coreos/etcd")
ETCD_IMAGE_TAG = os.environ.get("ETCD_IMAGE_TAG", 'v3.0.1')
ETCD_DEPLOYMENT_TYPE = os.environ.get('ETCD_DEPLOYMENT_TYPE', "docker")

SERVICE_PATH = os.environ.get('SERVICE_PATH')
TEMPEST_SCRIPT_PATH = os.environ.get('TEMPEST_SCRIPT_PATH')
SEARCH_DOMAINS = os.environ.get('SEARCH_DOMAINS',
                                'ccp.svc.cluster.local').split(',')
BUILDER_WORKERS = os.environ.get('BUILDER_WORKERS', 1)
BUILD_IMAGES = get_var_as_bool('BUILD_IMAGES', True)
REGISTRY = os.environ.get('REGISTRY', "127.0.0.1:31500")
IMAGES_NAMESPACE = os.environ.get('IMAGES_NAMESPACE', 'mcp')
IMAGES_TAG = os.environ.get('IMAGES_TAG', 'latest')


DEFAULT_CUSTOM_YAML = {
    "kube_network_plugin": KUBE_NETWORK_PLUGIN,
    "kube_proxy_mode": KUBE_PROXY_MODE,
    "docker_version": DOCKER_VERSION,
    "etcd_image_repo": ETCD_IMAGE_REPO,
    "etcd_image_tag": ETCD_IMAGE_TAG,
    "kube_hostpath_dynamic_provisioner": "{}".format(
        KUBE_HOSTPATH_DYNAMIC_PROVISIONER).lower(),
    "etcd_deployment_type": ETCD_DEPLOYMENT_TYPE,
    "hyperkube_image_tag": HYPERKUBE_IMAGE_TAG,
    "hyperkube_image_repo": HYPERKUBE_IMAGE_REPO,
    "ipip": IPIP_USAGE,
    "kube_version": KUBE_VERSION,
    "use_hyperkube_cni": str("true"),
    "searchdomains": SEARCH_DOMAINS,
}

CALICO = {
    "calico_node_image_repo": os.environ.get('CALICO_NODE_IMAGE_REPO'),
    "calico_node_image_tag": os.environ.get('CALICO_NODE_IMAGE_TAG'),
    "calicoctl_image_repo": os.environ.get('CALICOCTL_IMAGE_REPO'),
    "calico_version": os.environ.get('CALICO_VERSION'),
    "calico_cni_download_url": os.environ.get('CALICO_CNI_DOWNLOAD_URL'),
    "calico_cni_checksum": os.environ.get('CALICO_CNI_CHECKSUM'),
    "calico_cni_ipam_download_url": os.environ.get(
        'CALICO_CNI_IPAM_DOWNLOAD_URL'),
    "calico_cni_ipam_checksum": os.environ.get('CALICO_CNI_IPAM_CHECKSUM'),
}

for key, val in CALICO.items():
    if val:
        DEFAULT_CUSTOM_YAML[key] = val

DEPLOY_CONFIG = '/tmp/ccp-globals.yaml'

FUEL_CCP_KEYSTONE_LOCAL_REPO = os.environ.get('FUEL_CCP_KEYSTONE_LOCAL_REPO',
                                              None)

CCP_CONF = {
    'builder': {
        'workers': BUILDER_WORKERS,
        'push': True
    },
    'registry': {
        'address': REGISTRY
    },
    'repositories': {
        'skip_empty': True
    },
    'kubernetes': {
        'namespace': 'ccp'
    },
    'deploy_config': DEPLOY_CONFIG,
    'images': {
        'namespace': IMAGES_NAMESPACE,
        'tag': IMAGES_TAG
    }
}

CCP_CLI_PARAMS = {
    "config-file": "~/.ccp.yaml",
    "debug": "",
    "log-file": "ccp.log",
}

CCP_DEFAULT_GLOBALS = {
    "configs": {
        "private_interface": "eth0",
        "public_interface": "eth1",
        "neutron_external_interface": "eth2"
    }
}

NETCHECKER_SERVER_DIR = os.environ.get(
    'NETCHECKER_SERVER_DIR', os.path.join(os.getcwd(), 'mcp-netchecker-server')
)
NETCHECKER_AGENT_DIR = os.environ.get(
    'NETCHECKER_AGENT_DIR', os.path.join(os.getcwd(), 'mcp-netchecker-agent')
)
MCP_NETCHECKER_AGENT_IMAGE_REPO = os.environ.get(
    'MCP_NETCHECKER_AGENT_IMAGE_REPO')
MCP_NETCHECKER_AGENT_VERSION = os.environ.get(
    'MCP_NETCHECKER_AGENT_VERSION')
MCP_NETCHECKER_SERVER_IMAGE_REPO = os.environ.get(
    'MCP_NETCHECKER_SERVER_IMAGE_REPO')
MCP_NETCHECKER_SERVER_VERSION = os.environ.get(
    'MCP_NETCHECKER_SERVER_VERSION')

# Settings for AppController testing
# AC_ZIP_URL is used to get link for zip archive with AppController, and by
#  default it's built from AC_REPO (github link to AppController project) and
#  AC_COMMIT (specific commit or master). You should provide AC_REPO (with
#  or without AC_COMMIT) for now to pass AppController tests..
AC_COMMIT = os.environ.get("AC_COMMIT", "master")
AC_REPO = os.environ.get("AC_REPO", "")
AC_ZIP_URL = os.environ.get(
    "AC_ZIP_URL", "{repo}/archive/{commit}.zip".format(
        repo=AC_REPO, commit=AC_COMMIT))

LVM_PLUGIN_DIRNAME = os.environ.get("LVM_PLUGIN_DIRNAME", 'mirantis.com~lvm')
LVM_PLUGIN_DIR = os.path.join(
    '/usr/libexec/kubernetes/kubelet-plugins/volume/exec', LVM_PLUGIN_DIRNAME)
LVM_PLUGIN_PATH = os.environ.get("LVM_PLUGIN_PATH", "~/lvm")
LVM_FILENAME = os.path.basename(LVM_PLUGIN_PATH)
