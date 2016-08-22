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

    @classmethod
    def build_command(cls, *args, **kwargs):
        command_list = ['ccp']
        for arg in args:
            command_list.append('--{}'.format(arg.replace('_', '-')))
        for key in kwargs:
            command_list.append(
                '--{0} {1}'.format(key.replace('_', '-'), kwargs[key]))
        return ' '.join(command_list)

    def do_fetch(self, *args, **kwargs):
        cmd = self.build_command(*args, **kwargs) + " fetch"
        with self.__underlay.remote(
                host=self.__config.k8s.kube_host) as remote:
            remote.execute(cmd)

    def do_build(self, *args, **kwargs):
        cmd = self.build_command(*args, **kwargs) + " build"
        with self.__underlay.remote(
                host=self.__config.k8s.kube_host) as remote:
            LOG.info(
                "Running command '{cmd}' on node {node}".format(
                    cmd=cmd,
                    node=remote.hostname
                )
            )
            remote.execute(cmd)

    def do_deploy(self, *args, **kwargs):
        cmd = self.build_command(*args, **kwargs) + " deploy"
        with self.__underlay.remote(
                host=self.__config.k8s.kube_host) as remote:
            LOG.info(
                "Running command '{cmd}' on node {node}".format(
                    cmd=cmd,
                    node=remote.hostname
                )
            )
            remote.execute(cmd)

    def update_service(self, service_name):
        if not settings.SERVICE_PATH:
            raise exceptions.VariableNotSet('SERVICE_PATH')
        with self.__underlay.remote(
                host=self.__config.k8s.kube_host) as remote:
            remote.execute(
                'rm -rf ./microservices-repos/fuel-ccp-{}'
                .format(service_name))
            remote.upload(
                settings.SERVICE_PATH,
                "./microservices-repos/")
