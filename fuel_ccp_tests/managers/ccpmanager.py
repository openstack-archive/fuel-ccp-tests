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
                LOG.debug("*** Run cmd={0}".format(cmd))
                result = remote.check_call(cmd, verbose=True)
                LOG.debug("*** Result STDOUT:\n{0}".format(result.stdout_str))
                LOG.debug("*** Result STDERR:\n{0}".format(result.stderr_str))

    @classmethod
    def build_command(cls, *args, **kwargs):
        """Generate the list of parameters

        :param args: list of command parameters
        :param kwargs: dict of command parameters
        :param base_command: by default will be ccp, or taken from  kwargs
        :return: list of parameters
        """
        base_command = kwargs.pop('base_command', 'ccp')
        command_list = [base_command]
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

    def do_dry_run(self, *args, **kwargs):
        """Create yaml templates, make registry

        :param args: passed into build_command()
        :param kwargs: passed into build_command()
        :param export_dir: taken from kwargs, contains dir for yaml templates
        :param: base_command: should be empty for getting 'dry_run'
        params without 'ccp'
        :return: None
        """
        try:
            export_dir = kwargs.pop("export_dir")
        except KeyError:
            raise ValueError("Variable 'export_dir' is not set")
        command_list = [
            self.build_command(*args, **kwargs),
            "deploy",
            "--dry-run",
            self.build_command(export_dir=export_dir, base_command='')
        ]
        command_list = ' '.join(command_list)
        command = [
            command_list,
            'kubectl create -f {0}/configmaps/ -f {0}'.format(
                os.path.join('~/', export_dir))
        ]
        with self.__underlay.remote(
                host=self.__config.k8s.kube_host) as remote:
            for cmd in command:
                LOG.info("Running command '{cmd}' on node {node}".format(
                    cmd=cmd,
                    node=remote.hostname)
                )
                result = remote.execute(cmd)
                assert result['exit_code'] == 0
