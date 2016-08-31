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
import copy
import os
import pkg_resources

from oslo_config import cfg
from oslo_config import generator

from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests.helpers import oslo_cfg_types as ct
from fuel_ccp_tests import settings


_default_conf = pkg_resources.resource_filename(
    __name__, 'templates/default.yaml')


hardware_opts = [
    ct.Cfg('manager', ct.String(),
           help="Hardware manager name", default="devops"),
    ct.Cfg('conf_path', ct.String(),
           help="Hardware config file", default=_default_conf),

    ct.Cfg('current_snapshot', ct.String(),
           help="Latest environment status name",
           default=ext.SNAPSHOT.underlay),
]


underlay_opts = [
    ct.Cfg('ssh', ct.JSONList(),
           help="""SSH Settings for Underlay: [{
                  'node_name': node1,
                  'host': hostname,
                  'login': login,
                  'password': password,
                  'address_pool': (optional),
                  'port': (optional),
                  'keys': [(optional)],
                  }, ...]""", default=[]),
]

# TODO(ddmitriev): remove these variables from settings.py
#                  and use this settings from 'config':
# KUBE_ADMIN_USER = os.environ.get('KUBE_ADMIN_USER', 'root')
# KUBE_ADMIN_PASS = os.environ.get('KUBE_ADMIN_PASS', 'changeme')
# KUBE_HOST = os.environ.get('KUBE_HOST', None)
# KUBE_VERSION = os.environ.get("KUBE_VERSION", "v1.3.0")
# IPIP_USAGE = get_var_as_bool('IPIP_USAGE', True)
# DEPLOY_SCRIPT = os.environ.get("DEPLOY_SCRIPT", None)

# Deploy options for a new K8S cluster
k8s_deploy_opts = [
    ct.Cfg('kube_version', ct.String(),
           help="", default="v1.3.5"),
    ct.Cfg('ipip_usage', ct.Boolean(),
           help="", default=True),
    ct.Cfg('deploy_script', ct.String(),
           help="", default=None),
    ct.Cfg('kube_settings', ct.JSONDict(),
           help="", default=None),
]

# Access credentials to a ready K8S cluster
k8s_opts = [
    ct.Cfg('kube_admin_user', ct.String(),
           help="", default="root"),
    ct.Cfg('kube_admin_pass', ct.String(),
           help="", default="changeme"),
    ct.Cfg('kube_host', ct.IPAddress(),
           help="", default=None),
]


# PRIVATE_REGISTRY = os.environ.get('PRIVATE_REGISTRY', None)

# Deploy options for a new CCP
ccp_deploy_opts = [
    ct.Cfg('private_registry', ct.String(),
           help="", default=None),
]

# Access credentials to a ready CCP
ccp_opts = [
    # TODO: OpenStack endpoints, any other endpoints (galera? rabbit?)
    ct.Cfg('os_host', ct.IPAddress(),
           help="", default=None),
]


_group_opts = [
    ('hardware', hardware_opts),
    ('underlay', underlay_opts),
    ('k8s_deploy', k8s_deploy_opts),
    ('k8s', k8s_opts),
    ('ccp_deploy', ccp_deploy_opts),
    ('ccp', ccp_opts),
]


def register_opts(config):
    config.register_group(cfg.OptGroup(name='hardware',
                          title="Hardware settings", help=""))
    config.register_opts(group='hardware', opts=hardware_opts)

    config.register_group(cfg.OptGroup(name='underlay',
                          title="Underlay configuration", help=""))
    config.register_opts(group='underlay', opts=underlay_opts)

    config.register_group(cfg.OptGroup(name='k8s_deploy',
                          title="K8s deploy configuration", help=""))
    config.register_opts(group='k8s_deploy', opts=k8s_deploy_opts)

    config.register_group(cfg.OptGroup(name='k8s',
                          title="K8s config and credentials", help=""))
    config.register_opts(group='k8s', opts=k8s_opts)

    config.register_group(cfg.OptGroup(name='ccp_deploy',
                          title="CCP deploy configuration", help=""))
    config.register_opts(group='ccp_deploy', opts=ccp_deploy_opts)

    config.register_group(cfg.OptGroup(name='ccp',
                          title="CCP config and credentials", help=""))
    config.register_opts(group='ccp', opts=ccp_opts)
    return config


def load_config(config_files):
    config = cfg.CONF
    register_opts(config)
    config(args=[], default_config_files=config_files)
    return config


def reload_snapshot_config(config, snapshot_name):
    """Reset config to the state from test_config file"""
    test_config_path = os.path.join(
        settings.LOGS_DIR, 'config_{0}.ini'.format(snapshot_name))
    config(args=[], default_config_files=[test_config_path])
    return config


def list_opts():
    """Return a list of oslo.config options available in the fuel-ccp-tests.
    """
    return [(group, copy.deepcopy(opts)) for group, opts in _group_opts]


def list_current_opts(config):
    """Return a list of oslo.config options available in the fuel-ccp-tests.
    """
    result_opts = []
    for group, opts in _group_opts:
        current_opts = copy.deepcopy(opts)
        for opt in current_opts:
            if hasattr(config, group):
                if hasattr(config[group], opt.name):
                    opt.default = getattr(config[group], opt.name)
        result_opts.append((group, current_opts))
    return result_opts


def save_config(config, snapshot_name):
    test_config_path = os.path.join(
        settings.LOGS_DIR, 'config_{0}.ini'.format(snapshot_name))

    with open(test_config_path, 'w') as output_file:
        formatter = generator._OptFormatter(output_file=output_file)
        for group, opts in list_current_opts(config):
            formatter.format_group(group)
            for opt in opts:
                formatter.format(opt, group, minimal=True)
                formatter.write('\n')
            formatter.write('\n')
