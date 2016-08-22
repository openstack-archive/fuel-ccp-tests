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
from mcp_tests import settings
from mcp_tests import logger


LOG = logger.logger


class CCPManager(object):
    """docstring for CCPManager"""

    def __init__(self):
        super(CCPManager, self).__init__()

    @classmethod
    def install_ccp(cls, env):
        """Base action to deploy k8s by external deployment script"""
        LOG.info("Trying to install fuel-ccp on admin node")
        remote = env.node_ssh_client(
            env.k8s_nodes[0],
            login=settings.SSH_NODE_CREDENTIALS['login'],
            password=settings.SSH_NODE_CREDENTIALS['password'])

        ccp_repo_url = settings.CCP_REPO
        cmd = ('pip install --upgrade git+{}'.format(ccp_repo_url))
        with remote.get_sudo(remote):
            remote.check_call(cmd, verbose=True)
        remote.close()

    @classmethod
    def build_command(cls, *args, **kwargs):
        command_list = ['ccp']
        for arg in args:
            command_list.append('--{}'.format(arg.replace('_', '-')))
        for key in kwargs:
            command_list.append(
                '--{0} {1}'.format(key.replace('_', '-'), kwargs[key]))
        return ' '.join(command_list)

    @classmethod
    def do_fetch(cls, remote, *args, **kwargs):
        cmd = cls.build_command(*args, **kwargs) + " fetch"
        remote.execute(cmd)

    @classmethod
    def do_build(cls, remote, *args, **kwargs):
        cmd = cls.build_command(*args, **kwargs) + " build"
        remote.execute(cmd)

    @classmethod
    def do_deploy(cls, remote, *args, **kwargs):
        cmd = cls.build_command(*args, **kwargs) + " deploy"
        remote.execute(cmd)
