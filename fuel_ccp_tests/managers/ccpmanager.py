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

from devops.error import DevopsCalledProcessError

from fuel_ccp_tests.helpers import exceptions
from fuel_ccp_tests import settings
from fuel_ccp_tests import logger

LOG = logger.logger

CCP_CONF = """
[DEFAULT]
use_stderr = False
"""


class CCPManager(object):
    """docstring for CCPManager"""

    __config = None
    __underlay = None

    def __init__(self, config, underlay):
        self.__config = config
        self.__underlay = underlay
        super(CCPManager, self).__init__()

    def install_ccp(self, use_defaults=True):
        """Base action to deploy k8s by external deployment script"""
        LOG.info("Trying to install fuel-ccp on admin node")
        with self.__underlay.remote(
                host=self.__config.k8s.kube_host) as remote:

            ccp_repo_url = settings.CCP_REPO
            LOG.info("Fetch ccp from github")
            cmd = 'git clone {}'.format(ccp_repo_url)
            remote.check_call(cmd, verbose=True)

            LOG.info('Install fuel-ccp from local path')
            cmd = 'pip install --upgrade fuel-ccp/'
            with remote.get_sudo(remote):
                remote.check_call(cmd, verbose=True)

            if use_defaults:
                LOG.info("Use defaults config from ccp")
                cmd = ('cat fuel-ccp/etc/topology-example.yaml '
                       '>> /tmp/ccp-globals.yaml')
                remote.check_call(cmd, verbose=True)

    @property
    def default_params(self):
        if hasattr(self, '_default_params'):
            return self._default_params.copy()
        return None

    @default_params.setter
    def default_params(self, v):
        self._default_params = v.copy()

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
        cmd = "cat >> {path} << EOF\n{content}\nEOF".format(
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

    def run(self, cmd, components=None, params=None, suppress_output=False):
        params = self.__build_param_string(params)
        params = params or ''
        if components:
            if isinstance(components, str):
                components = [components]
            components = '-c {}'.format(' '.join(components))
        else:
            components = ''
        if suppress_output:
            ccp_out_redirect = ("> >(tee ccp.out.log > /dev/null) "
                                "2> >(tee ccp.err.log >/dev/null)")
        else:
            ccp_out_redirect = ""

        cmd = "ccp {params} {cmd} {components} {ccp_out_redirect}".format(
            params=params, cmd=cmd, components=components,
            ccp_out_redirect=ccp_out_redirect)

        LOG.info("Running {cmd}".format(cmd=cmd))
        with self.__underlay.remote(
                host=self.__config.k8s.kube_host) as remote:
            remote.check_call(cmd)

    def fetch(self, components=None, params=None):
        self.run('fetch',
                 components=components,
                 params=params)

    def build(self, components=None, params=None, suppress_output=True):
        try:
            self.run('build',
                     components=components,
                     params=params, suppress_output=suppress_output)
        except DevopsCalledProcessError as e:
            LOG.warning(e)
            LOG.info("Retry build command")
            self.run('build',
                     components=components,
                     params=params, suppress_output=suppress_output)

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
                path,
                "/home/{user}/microservices-repos/fuel-ccp-{service}".format(
                    user=settings.SSH_LOGIN,
                    service=service_name))
