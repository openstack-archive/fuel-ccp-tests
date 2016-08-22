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
import yaml

from mcp_tests import settings
from mcp_tests import logger
from mcp_tests.helpers import ext

LOG = logger.logger

CCP_CONF = """
[DEFAULT]
deploy_config = /tmp/ccp-globals.yaml

[builder]
push = True

[registry]
address = "127.0.0.1:31500"

[kubernetes]
namespace = "demo"

[repositories]
skip_empty = True"""


class CCPManager(object):
    """docstring for CCPManager"""

    def __init__(self, node, login=None, password=None, default_params=None):
        super(CCPManager, self).__init__()

        login = login or settings.SSH_NODE_CREDENTIALS['login']
        password = password or settings.SSH_NODE_CREDENTIALS['password']
        self._remote = node.remote(
            network_name=ext.NETWORK_TYPE.public,
            login=login,
            password=password,
            private_keys=None
        )
        self.default_params = default_params

    def install_ccp(self):
        """Base action to deploy k8s by external deployment script"""
        LOG.info("Trying to install fuel-ccp on admin node")
        ccp_repo_url = settings.CCP_REPO
        LOG.info("Fetch ccp from github")
        cmd = 'git clone {}'.format(ccp_repo_url)
        self._remote.check_call(cmd, verbose=True)
        LOG.info('Install fuel-ccp from local path')
        cmd = 'pip install --upgrade fuel-ccp/'
        with self._remote.get_sudo(self._remote):
            self._remote.check_call(cmd, verbose=True)

    def init_default_config(self):
        self.put_raw_config('~/ccp.conf', CCP_CONF)

    def put_yaml_config(self, path, config):
        """Convert config dict to yaml and put it to admin node at path

        :param path: path to config file
        :param config: dict with configuration data
        """
        content = yaml.dump(config, default_flow_style=False)
        cmd = "cat > {path} << EOF\n{content}\nEOF".format(
            path=path, content=content)
        self._remote.check_call(cmd)

    def put_raw_config(self, path, content):
        """Put config content to file on admin node at path

        :param path: path to config file
        :param config: raw configuration data
        """
        cmd = "cat > {path} << EOF\n{content}\nEOF".format(
            path=path, content=content)
        self._remote.check_call(cmd)

    def __build_param_string(self, params=None):
        if params is None:
            params = self.default_params
        else:
            merge = self.default_params.copy()
            merge.update(params)
            params = merge

        return ' '.join(["--{}={}".format(
            k, v) if v else "--{}".format(k) for (k, v) in params.items()])

    def run(self, cmd, components=None, params=None):
        params = self.__build_param_string(params)
        params = params or ''
        components = components or ''
        ccp_exec_log = "> >(tee -a ccp.log)"
        ccp_exec_errlog = "2> >(tee -a ccp.err.log >&2)"
        cmd = ("ccp {params} {cmd} {components} {exec_log} "
               "{ccp_exec_errlog}").format(
                   params=params, cmd=cmd, components=components,
                   exec_log=ccp_exec_log, ccp_exec_errlog=ccp_exec_errlog)
        LOG.info("Running {cmd}".format(cmd=cmd))
        self._remote.check_call(cmd, verbose=True)

    def fetch(self, components=None, params=None):
        self.run('fetch',
                 components=components,
                 params=params)

    def build(self, components=None, params=None):
        self.run('build',
                 components=components,
                 params=params)

    def deploy(self, components=None, params=None):
        self.run('deploy',
                 components=components,
                 params=params)

    def cleanup(self, components=None, params=None):
        self.run('cleanup',
                 components=components,
                 params=params)

    def show_dep(self, components=None, params=None):
        self.run('show-dep',
                 components=components,
                 params=params)
