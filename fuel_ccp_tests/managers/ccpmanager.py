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

import yaml

from devops.error import DevopsCalledProcessError

from fuel_ccp_tests.helpers import exceptions
from fuel_ccp_tests import settings
from fuel_ccp_tests import logger

LOG = logger.logger


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
                LOG.debug("*** Run cmd={0}".format(cmd))
                result = remote.check_call(cmd, verbose=True)
                LOG.debug("*** Result STDOUT:\n{0}".format(result.stdout_str))
                LOG.debug("*** Result STDERR:\n{0}".format(result.stderr_str))

    @property
    def default_params(self):
        if hasattr(self, '_default_params'):
            return self._default_params.copy()
        return None

    @default_params.setter
    def default_params(self, v):
        self._default_params = v.copy()

    def init_default_config(self, include_files=None):
        self.put_yaml_config(settings.CCP_CLI_PARAMS["config-file"],
                             settings.CCP_CONF)
        self.add_includes(settings.CCP_CLI_PARAMS["config-file"],
                          include_files)

    def add_includes(self, path, files):
        def clear_tilda(p):
            return p.replace('~/', '')

        content = "---\n!include\n{}".format(
            '\n'.join(['- ' + clear_tilda(f) for f in files]))
        cmd = 'echo "{content}" >> {path}'.format(
            path=path, content=content)
        with self.__underlay.remote(
                host=self.__config.k8s.kube_host) as remote:
            remote.execute(cmd)

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

    def get_raw_config(self, path):
        """Get config content from file at path on admin node

        :param path: path to config file
        :return: str
        """
        with self.__underlay.remote(
                host=self.__config.k8s.kube_host) as remote:
            return remote.open(path).read()

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

    def get_yaml_config(self, path):
        """Get config content from file at path on admin node

        :param path: path to config file
        :return: dict
        """
        with self.__underlay.remote(
                host=self.__config.k8s.kube_host) as remote:
            return yaml.load(remote.open(path))

    def __build_param_string(self, params=None):
        if params is None:
            params = self.default_params
        else:
            merge = self.default_params.copy()
            merge.update(params)
            params = merge

        return ' '.join(["--{}={}".format(
            k, v) if v else "--{}".format(k) for (k, v) in params.items()])

    def run(self, cmd, components=None, params=None,
            use_cli_params=False, suppress_output=False,
            raise_on_err=True, error_info=None,
            expected=None):

        if suppress_output:
            ccp_out_redirect = ("> >(tee ccp.out.log > /dev/null) "
                                "2> >(tee ccp.err.log >/dev/null)")
        else:
            ccp_out_redirect = ""
        if use_cli_params is True:
            params = self.__build_param_string(params)
            params = params or ''
            if components:
                if isinstance(components, str):
                    components = [components]
                components = '-c {}'.format(' '.join(components))
            else:
                components = ''

            cmd = "ccp {params} {cmd} {components} {ccp_out_redirect}".format(
                params=params, cmd=cmd, components=components,
                ccp_out_redirect=ccp_out_redirect)
        else:
            cmd = "ccp {cmd} {ccp_out_redirect}".format(
                cmd=cmd, ccp_out_redirect=ccp_out_redirect)

        LOG.info("Running {cmd}".format(cmd=cmd))
        with self.__underlay.remote(
                host=self.__config.k8s.kube_host) as remote:
            res = remote.check_call(cmd,
                                    raise_on_err=raise_on_err,
                                    error_info=error_info,
                                    expected=expected,
                                    verbose=True)
        return res

    def fetch(self,
              params=None,
              raise_on_err=True,
              error_info=None,
              expected=None):
        # build config file
        self.put_yaml_config(settings.CCP_FETCH_CONFIG, params)
        return self.run('fetch',
                        raise_on_err=raise_on_err,
                        error_info=error_info,
                        expected=expected)

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

    def dry_deploy(self, export_dir, components=None, params=None):
        self.run('deploy --dry-run --export-dir={export_dir}'.format(
                 export_dir=export_dir),
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
                'rm -rf ./ccp-repos/fuel-ccp-{}'
                .format(service_name))
            remote.upload(
                path,
                "/home/{user}/ccp-repos/fuel-ccp-{service}".format(
                    user=settings.SSH_LOGIN,
                    service=service_name))
