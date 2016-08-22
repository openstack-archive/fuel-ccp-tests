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
import pytest
import yaml

from mcp_tests import logger
from mcp_tests import settings
from mcp_tests.helpers import post_install_k8s_checks
from mcp_tests.helpers import post_os_deploy_checks
from mcp_tests.managers import k8s
from mcp_tests.managers import ccp

import base_test

LOG = logger.logger


class TestDeployOpenstack(base_test.SystemBaseTest):
    """Create VMs for mcpinstaller"""

    snapshot_microservices_build = 'snapshot_microservices_build'
    snapshot_microservices_deployed = 'snapshot_microservices_deployed'
    kube_settings = {
        "kube_network_plugin": "calico",
        "kube_proxy_mode": "iptables",
        "hyperkube_image_repo": "quay.io/coreos/hyperkube",
        "hyperkube_image_tag": "{0}_coreos.0".format(settings.KUBE_VERSION),
        "kube_version": settings.KUBE_VERSION,
        "ipip": settings.IPIP_USAGE,
        "images_namespace": settings.IMAGES_NAMESPACE,
        "docker_options": settings.REGISTRY,
        "docker_options": "--insecure-registry={0}".format(settings.REGISTRY),
        "upstream_dns_servers": settings.UPSTREAM_DNS,
    }

    def get_params(self, params_list, exclude_list=None):
        params = []
        for item in params_list:
            if isinstance(item, dict):
                if item.keys()[0] not in exclude_list:
                    params.append(item)
            else:
                if item not in exclude_list:
                    params.append(item)
        return params

    def create_registry(self, remote):
        registry_pod = os.getcwd() + '/mcp_tests/templates/' \
                                     'registry_templates/registry-pod.yaml'
        service_registry = os.getcwd() + '/mcp_tests/templates/' \
                                         'registry_templates/' \
                                         'service-registry.yaml'
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
                    node_name=remote.hostname
                )
            )
            result = remote.execute(cmd)
            assert result['exit_code'] == 0

    def pre_build_deploy_step(self, remote):
        topology_path = os.getcwd() + '/mcp_tests/templates/' \
                                      'k8s_templates/k8s_topology.yaml'
        remote.upload(topology_path, './')
        command = '>/var/log/microservices.log'
        with remote.get_sudo(remote):
            LOG.info(
                "Running command '{cmd}' on node {node_name}".format(
                    cmd=command,
                    node_name=remote.hostname
                )
            )
            result = remote.check_call(command, verbose=True)
            assert result['exit_code'] == 0

    @pytest.mark.snapshot_needed(name=snapshot_microservices_deployed)
    @pytest.mark.revert_snapshot(name=snapshot_microservices_build,
                                 strict=False)
    @pytest.mark.fail_snapshot
    def test_fuel_ccp_deploy_microservices(self, env, k8sclient):
        """Deploy base environment

        Scenario:
        1. Revert snapshot
        2. Install microservices
        3. Deploy environment
        4. Check deployment

        Duration 30 min
        """
        k8s.K8SManager.install_k8s(env, custom_yaml=self.kube_settings)
        ccp.CCPManager.install_ccp(env)

        k8s_node = env.k8s_nodes[0]
        remote = env.node_ssh_client(
            k8s_node,
            **settings.SSH_NODE_CREDENTIALS)
        self.pre_build_deploy_step(remote)

        registry = None
        if settings.BUILD_IMAGES:
            registry = '127.0.0.1:31500'
            self.create_registry(remote)
            yaml_path = os.getcwd() + '/mcp_tests/templates/' \
                                      'k8s_templates/build-deploy_cluster.yaml'
            with open(yaml_path, 'r') as yaml_path:
                data = yaml_path.read()
                data = data.format(registry_address=registry,
                                   images_namespace=settings.IMAGES_NAMESPACE,
                                   images_tag=settings.IMAGES_TAG,
                                   deploy_config='~/k8s_topology.yaml')
                params_list = yaml.load(data)['ccp-microservices-options']
            with remote.get_sudo(remote):
                ccp.CCPManager.do_build(remote, **params_list)
            post_install_k8s_checks.check_calico_network(remote, env)
        else:
            registry = settings.REGISTRY
            if not registry:
                raise ValueError("The REGISTRY variable should be set with "
                                 "external registry address, "
                                 "current value {0}".format(settings.REGISTRY))

        exclude_list = ['builder-push', 'builder-workers']
        yaml_path = os.getcwd() + '/mcp_tests/templates/k8s_templates/' \
                                  'build-deploy_cluster.yaml'

        with open(yaml_path, 'r') as yaml_path:
            data = yaml_path.read()
            data = data.format(registry_address=registry,
                               images_namespace=settings.IMAGES_NAMESPACE,
                               images_tag=settings.IMAGES_TAG,
                               deploy_config='~/k8s_topology.yaml')
            params_list = yaml.load(data)['ccp-microservices-options']
            params = self.get_params(params_list, exclude_list)
            params_dict = {}
            for item in filter(
                    lambda x: isinstance(x, dict), params):
                params_dict.update(item)
            params_list = [item for item in params if not isinstance(
                           item, dict)]
        with remote.get_sudo(remote):
            ccp.CCPManager.do_deploy(remote, *params_list, **params_dict)
        post_os_deploy_checks.check_jobs_status(k8sclient, timeout=1500,
                                                namespace='ccp')
        post_os_deploy_checks.check_pods_status(k8sclient, timeout=1500,
                                                namespace='ccp')
