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

    def mark_lvm_nodes(self, lvm_config):
        if lvm_config:
            lvm_mark = {"lvm": "on"}
            # Get nodes ips
            lvm_nodes_ips = [self.__underlay.host_by_node_name(node_name)
                             for node_name in lvm_config]
            # Get only those K8sNodes, which has ips from lvm_nodes_ips
            lvm_nodes = [
                node for node in self.api.nodes.list()
                if any(
                    ip.address in lvm_nodes_ips for ip in node.addresses)]

            for node in lvm_nodes:
                node.add_labels(lvm_mark)

    def upload_lvm_plugin(self, node_name):
        LOG.info("Uploading LVM plugin to node '{}'".format(node_name))
        if self.__underlay:
            with self.__underlay.remote(node_name=node_name) as remote:
                remote.upload(settings.LVM_PLUGIN_PATH, '/tmp/')
                with remote.get_sudo(remote):
                    remote.check_call(
                        'mkdir -p {}'.format(settings.LVM_PLUGIN_DIR),
                        verbose=True
                    )
                    remote.check_call(
                        "mv /tmp/{} {}".format(settings.LVM_FILENAME,
                                               settings.LVM_PLUGIN_DIR),
                        verbose=True
                    )
                    remote.check_call(
                        "chmod +x {}/{}".format(settings.LVM_PLUGIN_DIR,
                                                settings.LVM_FILENAME),
                        verbose=True
                    )

    def install_k8s(self, custom_yaml=None, env_var=None,
                    k8s_admin_ip=None, k8s_slave_ips=None,
                    expected_ec=None, verbose=True, lvm_config=None):
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

        if lvm_config:
            LOG.info("uploading LVM plugin for k8s")
            for node_name in lvm_config:
                self.upload_lvm_plugin(node_name)

        environment_variables = {
            "SLAVE_IPS": " ".join(k8s_slave_ips),
            "ADMIN_IP": k8s_admin_ip,
            "KARGO_REPO": settings.KARGO_REPO,
            "KARGO_COMMIT": settings.KARGO_COMMIT
        }
        if custom_yaml:
            self.set_dns(custom_yaml)
            environment_variables.update(
                {"CUSTOM_YAML": yaml.safe_dump(
                    custom_yaml, default_flow_style=False)}
            )
        if env_var:
            environment_variables.update(env_var)

        # Return to original dict after moving to fuel-devops3.0.2
        # current_env.update(dict=environment_variables)
        current_env = environment_variables

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

        self.mark_lvm_nodes(lvm_config)

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
        """Create Pod and SErvice for K8S registry"""

        registry_pod = os.getcwd() + '/fuel_ccp_tests/templates/' \
                                     'registry_templates/registry-pod.yaml'
        service_registry = os.getcwd() + '/fuel_ccp_tests/templates/' \
                                         'registry_templates/' \
                                         'service-registry.yaml'

        with file(registry_pod) as f:
            registry = yaml.load(f)
        with file(service_registry) as f:
            service = yaml.load(f)

        registry_pod = self.api.pods.create(body=registry, namespace='default')
        self.api.services.create(body=service, namespace='default')

        registry_pod.wait_running()

    def get_pod_phase(self, pod_name, namespace=None):
        return self.api.pods.get(
            name=pod_name, namespace=namespace).phase

    def wait_pod_phase(self, pod_name, phase, namespace=None, timeout=60):
        """Wait phase of pod_name from namespace while timeout

        :param str: pod_name
        :param str: namespace
        :param list or str: phase
        :param int: timeout

        :rtype: None
        """
        if isinstance(phase, str):
            phase = [phase]

        def check():
            return self.get_pod_phase(pod_name, namespace) in phase

        helpers.wait(check, timeout=timeout,
                     timeout_msg='Timeout waiting, pod {pod_name} is not in '
                                 '"{phase}" phase'.format(
                                     pod_name=pod_name, phase=phase))

    def check_pod_create(self, body, timeout=300, interval=5):
        """Check creating sample pod

        :param k8s_pod: V1Pod
        :param k8sclient: K8sCluster
        :rtype: V1Pod
        """
        LOG.info("Creating pod in k8s cluster")
        LOG.debug(
            "POD spec to create:\n{}".format(
                yaml.dump(body, default_flow_style=False))
        )
        LOG.debug("Timeout for creation is set to {}".format(timeout))
        LOG.debug("Checking interval is set to {}".format(interval))
        pod = self.api.pods.create(body=body)
        pod.wait_running(timeout=300, interval=5)
        LOG.info("Pod '{}' is created".format(pod.metadata.name))
        return self.api.pods.get(name=pod.metadata.name)

    def wait_pod_deleted(self, podname, timeout=60, interval=5):
        helpers.wait(
            lambda: podname not in [pod.name for pod in self.api.pods.list()],
            timeout=timeout,
            interval=interval,
            timeout_msg="Pod deletion timeout reached!"
        )

    def check_pod_delete(self, k8s_pod, timeout=300, interval=5):
        """Deleting pod from k8s

        :param k8s_pod: fuel_ccp_tests.managers.k8s.nodes.K8sNode
        :param k8sclient: fuel_ccp_tests.managers.k8s.cluster.K8sCluster
        """
        LOG.info("Deleting pod '{}'".format(k8s_pod.name))
        LOG.debug("Pod status:\n{}".format(k8s_pod.status))
        LOG.debug("Timeout for deletion is set to {}".format(timeout))
        LOG.debug("Checking interval is set to {}".format(interval))
        self.api.pods.delete(body=k8s_pod, name=k8s_pod.name)
        self.wait_pod_deleted(k8s_pod.name, timeout, interval)
        LOG.debug("Pod '{}' is deleted".format(k8s_pod.name))

    def check_service_create(self, body):
        """Check creating k8s service

        :param body: dict, service spec
        :param k8sclient: K8sCluster object
        :rtype: K8sService object
        """
        LOG.info("Creating service in k8s cluster")
        LOG.debug(
            "Service spec to create:\n{}".format(
                yaml.dump(body, default_flow_style=False))
        )
        service = self.api.services.create(body=body)
        LOG.info("Service '{}' is created".format(service.metadata.name))
        return self.api.services.get(name=service.metadata.name)

    def check_ds_create(self, body):
        """Check creating k8s DaemonSet

        :param body: dict, DaemonSet spec
        :param k8sclient: K8sCluster object
        :rtype: K8sDaemonSet object
        """
        LOG.info("Creating DaemonSet in k8s cluster")
        LOG.debug(
            "DaemonSet spec to create:\n{}".format(
                yaml.dump(body, default_flow_style=False))
        )
        ds = self.api.daemonsets.create(body=body)
        LOG.info("DaemonSet '{}' is created".format(ds.metadata.name))
        return self.api.daemonsets.get(name=ds.metadata.name)

    def create_objects(self, path):
        if isinstance(path, str):
            path = [path]
        params = ' '.join(["-f {}".format(p) for p in path])
        cmd = 'kubectl create {params}'.format(params=params)
        with self.__underlay.remote(
                host=self.__config.k8s.kube_host) as remote:
            LOG.info("Running command '{cmd}' on node {node}".format(
                cmd=cmd,
                node=remote.hostname)
            )
            result = remote.check_call(cmd)
            LOG.info(result['stdout'])

    def set_dns(self, k8s_settings):
        if 'nameservers' in k8s_settings:
            return
        if not self.__config.underlay.nameservers:
            return
        k8s_settings['nameservers'] = self.__config.underlay.nameservers
        LOG.info('Added custom DNS servers to the settings: '
                 '{0}'.format(k8s_settings['nameservers']))
