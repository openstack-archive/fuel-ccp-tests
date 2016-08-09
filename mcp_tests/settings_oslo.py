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

from oslo_config import cfg
from mcp_tests.helpers import oslo_cfg_types as ct


hardware_opts = [
    ct.Cfg('manager', ct.String(),
           help="Hardware manager name", default="devops"),
    ct.Cfg('conf_path', ct.String(),
           help="Hardware config file", default=None),
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


_group_opts = [
    ('hardware', hardware_opts),
    ('underlay', underlay_opts),
]


def register_hardware_opts(config):
    config.register_group(cfg.OptGroup(name='hardware',
                          title="Hardware settings", help=""))
    config.register_opts(group='hardware', opts=hardware_opts)
    return config


def register_underlay_opts(config):
    config.register_group(cfg.OptGroup(name='underlay',
                          title="Underlay configuration", help=""))
    config.register_opts(group='underlay', opts=underlay_opts)
    return config


def load_config(config_files):
    config = cfg.CONF
    register_hardware_opts(config)
    register_underlay_opts(config)
    config(args=[], default_config_files=config_files)
    return config


def list_opts():
    """Return a list of oslo.config options available in the fuel-ccp-tests.
    """
    return [(group, copy.deepcopy(opts)) for group, opts in _group_opts]
