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

from fuel_ccp_tests.helpers import ext

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
# FIXME(vshypyguzov) Decrease timeout when CI issues are resolved
KARGO_TIMEOUT = int(os.environ.get('KARGO_TIMEOUT', 3600))

KUBE_HOSTPATH_DYNAMIC_PROVISIONER = get_var_as_bool(
    'KUBE_HOSTPATH_DYNAMIC_PROVISIONER', True)
KUBE_ADMIN_USER = os.environ.get('KUBE_ADMIN_USER', 'root')
KUBE_ADMIN_PASS = os.environ.get('KUBE_ADMIN_PASS', 'changeme')
KUBE_HOST = os.environ.get('KUBE_HOST', None)
KUBE_VERSION = os.environ.get("KUBE_VERSION", "v1.4.0")

KUBE_NETWORK_PLUGIN = os.environ.get("KUBE_NETWORK_PLUGIN", "calico")
KUBE_PROXY_MODE = os.environ.get("KUBE_PROXY_MODE", "iptables")
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
IMAGES_TAG = os.environ.get('IMAGES_TAG', 'newton')


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
    "kube_version": KUBE_VERSION,
    "searchdomains": SEARCH_DOMAINS,
}

CALICO = {
    "calico_node_image_repo": os.environ.get('CALICO_NODE_IMAGE_REPO'),
    "calico_node_image_tag": os.environ.get('CALICO_NODE_IMAGE_TAG'),
    "calicoctl_image_repo": os.environ.get('CALICOCTL_IMAGE_REPO'),
    "calicoctl_image_tag": os.environ.get('CALICOCTL_IMAGE_TAG'),
    "calico_version": os.environ.get('CALICO_VERSION'),
    "calico_cni_image_repo": os.environ.get('CALICO_CNI_IMAGE_REPO'),
    "calico_cni_image_tag": os.environ.get('CALICO_CNI_IMAGE_TAG'),
    "ipip": get_var_as_bool('IPIP_USAGE', None),
    "overwrite_hyperkube_cni": get_var_as_bool('OVERWRITE_HYPERKUBE_CNI',
                                               None),
    "enable_network_policy": get_var_as_bool('ENABLE_NETWORK_POLICY',
                                             None),
    "deploy_netchecker": get_var_as_bool('DEPLOY_NETCHECKER',
                                         None),
}

for key, val in CALICO.items():
    if val is not None:
        DEFAULT_CUSTOM_YAML[key] = val

CCP_DEPLOY_CONFIG = '~/.ccp.deploy-config.yaml'
CCP_DEPLOY_TOPOLOGY = '~/.ccp.deploy-topology.yaml'
TOPOLOGY_PATH = os.environ.get('TOPOLOGY_PATH',
                               os.getcwd() + '/fuel_ccp_tests/templates/'
                               'k8s_templates/k8s_topology.yaml')


FUEL_CCP_KEYSTONE_LOCAL_REPO = os.environ.get('FUEL_CCP_KEYSTONE_LOCAL_REPO',
                                              None)
FUEL_CCP_ORIGIN_URL = os.environ.get(
    'FUEL_CCP_ORIGIN_URL',
    'https://git.openstack.org:443/openstack/')

OS_RELEASE = os.environ.get('OS_RELEASE', 'stable/newton')
OS_REPOS = {
    "openstack/horizon": {
        "git_url": "https://github.com/openstack/horizon.git",
        "git_ref": OS_RELEASE
    },
    "openstack/keystone": {
        "git_url": "https://github.com/openstack/keystone.git",
        "git_ref": OS_RELEASE
    },
    "openstack/nova": {
        "git_url": "https://github.com/openstack/nova.git",
        "git_ref": OS_RELEASE
    },
    "openstack/glance": {
        "git_url": "https://github.com/openstack/glance.git",
        "git_ref": OS_RELEASE
    },
    "openstack/heat": {
        "git_url": "https://github.com/openstack/heat.git",
        "git_ref": OS_RELEASE
    },
    "openstack/neutron": {
        "git_url": "https://github.com/openstack/neutron.git",
        "git_ref": OS_RELEASE
    },
    "openstack/sahara": {
        "git_url": "https://github.com/openstack/sahara.git",
        "git_ref": OS_RELEASE
    },
    "openstack/sahara-dashboard": {
        "git_url": "https://github.com/openstack/sahara-dashboard.git",
        "git_ref": OS_RELEASE
    },
    "openstack/murano": {
        "git_url": "https://github.com/openstack/murano.git",
        "git_ref": OS_RELEASE
    },
    "openstack/murano-dashboard": {
        "git_url": "https://github.com/openstack/murano-dashboard.git",
        "git_ref": OS_RELEASE
    },
    "openstack/cinder": {
        "git_url": "https://github.com/openstack/cinder.git",
        "git_ref": OS_RELEASE
    },
    "openstack/ironic": {
        "git_url": "https://github.com/openstack/ironic.git",
        "git_ref": OS_RELEASE
    }
}

CCP_CONF = {
    'builder': {
        'workers': BUILDER_WORKERS,
        'push': True
    },
    'registry': {
        'address': REGISTRY
    },
    'kubernetes': {
        'namespace': 'ccp'
    },
    'images': {
        'namespace': IMAGES_NAMESPACE,
        'tag': IMAGES_TAG
    }
}

CCP_SOURCES_CONFIG = '~/.ccp.build-sources.yaml'

CCP_FETCH_CONFIG = '~/.ccp.fetch.yaml'

CCP_FETCH_PARAMS = {
    'repositories': {
        'skip_empty': True
    }
}

CCP_BUILD_SOURCES = {
    'sources': OS_REPOS
}

CCP_CLI_PARAMS = {
    "config-file": "~/.ccp.yaml",
    "debug": "",
    "log-file": "ccp.log",
}

IFACES = {
    "public": os.environ.get("IFACE_PUBLIC", "ens3"),
    "private": os.environ.get("IFACE_PRIVATE", "ens4"),
    "neutron": os.environ.get("IFACE_NEUTRON", "ens5"),
}

CCP_DEFAULT_GLOBALS = {
    "configs": {
        "private_interface": IFACES['private'],
        "public_interface": IFACES['public'],
        "neutron_external_interface": IFACES['neutron']
    }
}

CCP_APT_CACHE_CONFIG = "~/.ccp.apt-cache.yaml"

CCP_APT_CACHE_PARAMS = {
    'url': {
        'debian': 'http://172.18.229.26:3142/debian',
        'security': 'http://172.18.229.26:3142/security',
        'ceph': {'debian': {'repo': 'http://172.18.229.26:3142/ceph'}},
        'mariadb': {'debian': {'repo': 'http://172.18.229.26:3142/mariadb'}}}}

CCP_ENVIRONMENT_PARAMS = {
    "microservices_home": "$HOME/ccp-repos"
}

NETCHECKER_SERVER_DIR = os.environ.get(
    'NETCHECKER_SERVER_DIR', os.path.join(os.getcwd(), 'mcp-netchecker-server')
)
NETCHECKER_AGENT_DIR = os.environ.get(
    'NETCHECKER_AGENT_DIR', os.path.join(os.getcwd(), 'mcp-netchecker-agent')
)
MCP_NETCHECKER_AGENT_IMAGE_REPO = os.environ.get(
    'MCP_NETCHECKER_AGENT_IMAGE_REPO',
    'quay.io/l23network/mcp-netchecker-agent')
MCP_NETCHECKER_AGENT_VERSION = os.environ.get(
    'MCP_NETCHECKER_AGENT_VERSION', 'latest')
MCP_NETCHECKER_SERVER_IMAGE_REPO = os.environ.get(
    'MCP_NETCHECKER_SERVER_IMAGE_REPO',
    'quay.io/l23network/mcp-netchecker-server')
MCP_NETCHECKER_SERVER_VERSION = os.environ.get(
    'MCP_NETCHECKER_SERVER_VERSION', 'latest')

# Settings for AppController testing
# AC_PATH - path to k8s-AppController repo
AC_PATH = os.environ.get("AC_PATH")

LVM_PLUGIN_DIRNAME = os.environ.get("LVM_PLUGIN_DIRNAME", 'mirantis.com~lvm')
LVM_PLUGIN_DIR = os.path.join(
    '/usr/libexec/kubernetes/kubelet-plugins/volume/exec', LVM_PLUGIN_DIRNAME)
LVM_PLUGIN_PATH = os.environ.get("LVM_PLUGIN_PATH", "~/lvm")
LVM_FILENAME = os.path.basename(LVM_PLUGIN_PATH)

PRECOMMIT_SNAPSHOT_NAME = os.environ.get(
    'PRECOMMIT_SNAPSHOT_NAME', ext.SNAPSHOT.ccp_deployed)
