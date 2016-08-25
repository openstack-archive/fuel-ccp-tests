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

from fuel_ccp_tests.helpers import exceptions
from fuel_ccp_tests import settings
from fuel_ccp_tests import logger

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

    __config = None
    __underlay = None

    def __init__(self, config, underlay):
        self.__config = config
        self.__underlay = underlay
        super(CCPManager, self).__init__()

    def install_ccp(self):
        """Base action to deploy k8s by external deployment script"""
        LOG.info("Trying to install fuel-ccp on admin node")
        with self.__underlay.remote(
                host=self.__config.k8s.kube_host) as remote:

            ccp_repo_url = settings.CCP_REPO
            cmd = ('pip install --upgrade git+{}'.format(ccp_repo_url))
            with remote.get_sudo(remote):
                # TODO(ddmitriev): log output
                remote.check_call(cmd, verbose=True)

    @property
    def default_params(self):
        if hasattr(self, '_default_params'):
            return self.default_params
        return None

    @default_params.setter
    def default_params(self, v):
        self._default_params = v

    def init_default_config(self):
        self.put_raw_config('~/ccp.conf', CCP_CONF)

    def put_raw_config(self, path, content):
        """Put config content to file on admin node at path

        :param path: path to config file
        :param config: raw configuration data
        """
        cmd = "cat > {path} << EOF\n{content}\nEOF".format(
            path=path, content=content)
        with self.__underlay.remote(
                host=self.__config.k8s.kube_host) as remote:
            remote.execute(cmd)

    def put_yaml_config(self, path, config):
        """Convert config dict to yaml and put it to admin node at path

        :param path: path to config file
        :param config: dict with configuration data
        """
        content = yaml.dump(config, default_flow_style=False)
        cmd = "cat > {path} << EOF\n{content}\nEOF".format(
            path=path, content=content)
        with self.__underlay.remote(
                host=self.__config.k8s.kube_host) as remote:
            remote.execute(cmd)

    @classmethod
    def build_command(cls, *args, **kwargs):
        command_list = ['ccp']
        for arg in args:
            command_list.append('--{}'.format(arg.replace('_', '-')))
        for key in kwargs:
            command_list.append(
                '--{0} {1}'.format(key.replace('_', '-'), kwargs[key]))
        return ' '.join(command_list)

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
        self.run('fetch',
                 components=components,
                 params=params)

    def deploy(self, components=None, params=None):
        self.run('fetch',
                 components=components,
                 params=params)

    def cleanup(self, components=None, params=None):
        self.run('fetch',
                 components=components,
                 params=params)

    def show_dep(self, components=None, params=None):
        self.run('fetch',
                 components=components,
                 params=params)

    def update_service(self, service_name, path=None):
        if not settings.SERVICE_PATH and not path:
            raise exceptions.VariableNotSet('SERVICE_PATH')

        path = path or settings.SERVICE_PATH
        with self.__underlay.remote(
                host=self.__config.k8s.kube_host) as remote:
            remote.execute(
                'rm -rf ./microservices-repos/fuel-ccp-{}'
                .format(service_name))
            remote.upload(
                settings.SERVICE_PATH,
                "./microservices-repos/")
