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

from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.managers.k8s import cluster


LOG = logger.logger


class K8SManager(object):
    """docstring for K8SManager"""

    def __init__(self):
        super(K8SManager, self).__init__()

    @classmethod
    def install_k8s(cls, underlay, custom_yaml=None, env_var=None,
                    k8s_admin_ip=None, k8s_slave_ips=None):
        """Action to deploy k8s by fuel-ccp-installer script

        Additional steps:
            Add vagrant user to docker group

        :param env: EnvManager
        :param kube_settings: Dict
        :param custom_yaml: False if deploy with kargo default, None if deploy
            with environment settings, or put you own
        """
        LOG.info("Trying to install k8s")
        current_env = copy.deepcopy(os.environ)

        k8s_nodes = underlay.node_names()
        if k8s_admin_ip is None:
            k8s_admin_ip = underlay.host_by_node_name(k8s_nodes[0])
        if k8s_slave_ips is None:
            k8s_slave_ips = [underlay.host_by_node_name(k8s_node)
                             for k8s_node in k8s_nodes]

        environment_variables = {
            "SLAVE_IPS": " ".join(k8s_slave_ips),
            "ADMIN_IP": k8s_admin_ip,
            "KARGO_REPO": settings.KARGO_REPO,
            "KARGO_COMMIT": settings.KARGO_COMMIT
        }
        if custom_yaml:
            environment_variables.update(
                {"CUSTOM_YAML": yaml.dump(
                    custom_yaml, default_flow_style=False)}
            )
        if env_var:
            environment_variables.update(env_var)
        current_env.update(dict=environment_variables)
        cls.deploy_k8s(environ=current_env)

        for node_name in k8s_nodes:
            with underlay.remote(node_name=node_name) as remote:
                LOG.info("Add vagrant to docker group")
                remote.check_call('sudo usermod -aG docker vagrant')

        return k8s_admin_ip

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

    @classmethod
    def get_k8sclient(cls, config, default_namespace=None):
        k8sclient = cluster.K8sCluster(user=config.k8s.kube_admin_user,
                                       password=config.k8s.kube_admin_pass,
                                       host=config.k8s.kube_host)
        return k8sclient
