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
import os

import yaml

from devops.helpers import helpers

from fuel_ccp_tests.helpers import exceptions
from fuel_ccp_tests.helpers import _subprocess_runner
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.managers.k8s import cluster

LOG = logger.logger


class K8SManager(object):
    """docstring for K8SManager"""

    __config = None
    __underlay = None

    def __init__(self, config, underlay):
        self.__config = config
        self.__underlay = underlay
        self._api_client = None
        super(K8SManager, self).__init__()

    def install_k8s(self, custom_yaml=None, env_var=None,
                    k8s_admin_ip=None, k8s_slave_ips=None,
                    expected_ec=None, verbose=True):
        """Action to deploy k8s by fuel-ccp-installer script

        Additional steps:
            Add vagrant user to docker group

        :param env: EnvManager
        :param kube_settings: Dict
        :param custom_yaml: False if deploy with kargo default, None if deploy
            with environment settings, or put you own
        :rtype: None
        """
        LOG.info("Trying to install k8s")
        current_env = copy.deepcopy(os.environ)

        k8s_nodes = self.__underlay.node_names()
        if k8s_admin_ip is None:
            k8s_admin_ip = self.__underlay.host_by_node_name(k8s_nodes[0])
        if k8s_slave_ips is None:
            k8s_slave_ips = [self.__underlay.host_by_node_name(k8s_node)
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

        # TODO(ddmitriev): replace with check_call(...,env=current_env)
        # when migrate to fuel-devops-3.0.2
        environ_str = ';'.join([
            "export {0}='{1}'".format(key, value)
            for key, value in current_env.items()])
        cmd = environ_str + ' ; ' + settings.DEPLOY_SCRIPT

        LOG.info("Run k8s deployment")

        # Use Subprocess.execute instead of Subprocess.check_call until
        # check_call is not fixed (fuel-devops3.0.2)
        result = _subprocess_runner.Subprocess.execute(cmd, verbose=verbose,
                                                       timeout=2400)
        if expected_ec is None:
            expected_ec = [0]
        if result.exit_code not in expected_ec:
            raise exceptions.UnexpectedExitCode(
                cmd,
                result.exit_code,
                expected_ec,
                stdout=result.stdout_brief,
                stderr=result.stdout_brief)

        for node_name in k8s_nodes:
            with self.__underlay.remote(node_name=node_name) as remote:
                LOG.info("Add vagrant to docker group")
                remote.check_call('sudo usermod -aG docker vagrant')

        self.__config.k8s.kube_host = k8s_admin_ip

        return result

    @property
    def api(self):
        if self._api_client is None:
            self._api_client = cluster.K8sCluster(
                user=self.__config.k8s.kube_admin_user,
                password=self.__config.k8s.kube_admin_pass,
                host=self.__config.k8s.kube_host,
                default_namespace='default')
        return self._api_client

    def create_registry(self):
        """Create Pod and SErvice for K8S registry

        TODO:
            Migrate to k8sclient
        """
        registry_pod = os.getcwd() + '/fuel_ccp_tests/templates/' \
                                     'registry_templates/registry-pod.yaml'
        service_registry = os.getcwd() + '/fuel_ccp_tests/templates/' \
                                         'registry_templates/' \
                                         'service-registry.yaml'

        with self.__underlay.remote(
                host=self.__config.k8s.kube_host) as remote:

            for item in registry_pod, service_registry:
                remote.upload(item, './')
            command = [
                'kubectl create -f ~/{0}'.format(registry_pod.split('/')[-1]),
                'kubectl create -f ~/{0}'.format(
                    service_registry.split('/')[-1]),
            ]
            for cmd in command:
                LOG.info(
                    "Running command '{cmd}' on node {node_name}".format(
                        cmd=cmd,
                        node_name=remote.hostname))
                result = remote.execute(cmd)
                if result['exit_code'] != 0:
                    raise SystemError(
                        "Registry wasn't created. "
                        "Command '{}' returned non-zero exit code({}). Err: "
                        "{}".format(
                            cmd, result['exit_code'], result['stderr_str']))

        self.wait_pod_phase('registry', 'default', 'Running', timeout=60)

    def get_pod_phase(self, pod_name, namespace):
        return self.api.pods.get(
            name=pod_name, namespace=namespace).phase

    def wait_pod_phase(self, pod_name, namespace, phase, timeout=60):
        def check():
            return self.get_pod_phase(pod_name, namespace) == phase

        helpers.wait(check, timeout=timeout,
                     timeout_msg='Timeout waiting, pod {pod_name} is not in '
                                 '"{phase}" phase'.format(
                                     pod_name=pod_name, phase=phase))
