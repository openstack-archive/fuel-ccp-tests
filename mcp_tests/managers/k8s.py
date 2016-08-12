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
import subprocess
import os

import yaml

from mcp_tests import logger
from mcp_tests import settings


LOG = logger.logger


class K8SManager(object):
    """docstring for K8SManager"""

    def __init__(self, arg):
        super(K8SManager, self).__init__()
        self.arg = arg

    @classmethod
    def install_k8s(cls, env, custom_yaml=None, env_var=None):
        """Action to deploy k8s by fuel-ccp-installer script

        Additional steps:
            Add vagrant user to docker group

        :param env: EnvManager
        :param kube_settings: Dict
        :param custom_yaml: False if deploy with kargo default, None if deploy
            with environment settings, or put you own
        """
        LOG.info("Trying to install k8s")
        snapshot_name = 'k8s_deployed'
        if not env.has_snapshot(snapshot_name):
            current_env = copy.deepcopy(os.environ)
            environment_variables = {
                "SLAVE_IPS": " ".join(env.k8s_ips),
                "ADMIN_IP": env.k8s_ips[0],
                "KARGO_REPO": settings.KARGO_REPO,
                "KARGO_COMMIT": settings.KARGO_COMMIT
            }
            if custom_yaml:
                environment_variables.update(
                    {"CUSTOM_YAML": yaml.dump(
                        custom_yaml, default_flow_style=False)}
                )
            current_env.update(dict=environment_variables)
            if env_var:
                environment_variables.update(env_var)
            cls.deploy_k8s(environ=current_env)
            remote = env.node_ssh_client(
                env.k8s_nodes[0],
                login=settings.SSH_NODE_CREDENTIALS['login'],
                password=settings.SSH_NODE_CREDENTIALS['password'])
            LOG.info("Add vagrant to docker group")
            remote.check_call('sudo usermod -aG docker vagrant')
            remote.close()
            env.create_snapshot(snapshot_name)
        else:
            LOG.info("Snapshot '{}' found, trying to revert".format(
                snapshot_name))
            env.revert_snapshot(snapshot_name)

    @classmethod
    def deploy_k8s(cls, environ=os.environ):
        """Base action to deploy k8s by external deployment script"""
        LOG.info("Run k8s deployment")
        try:
            process = subprocess.Popen([settings.DEPLOY_SCRIPT],
                                       env=environ,
                                       shell=True,
                                       bufsize=0,
                                       )
            assert process.wait() == 0
        except (SystemExit, KeyboardInterrupt) as err:
            process.terminate()
            raise err
