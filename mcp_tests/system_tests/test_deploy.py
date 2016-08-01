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
import base_test
import os
import pytest
import yaml

from mcp_tests import logger
from mcp_tests import settings
from mcp_tests.helpers import post_install_k8s_checks
from mcp_tests.helpers import post_os_deploy_checks

LOG = logger.logger


@pytest.mark.usefixtures("pre_build_deploy_step")
class TestDeployOpenstack(base_test.SystemBaseTest):
    """Create VMs for mcpinstaller"""

    namespace = 'default'
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

    def get_params(self, params_list, exclude_list):
        params = [param for param in params_list if param not in exclude_list]
        return params

    @pytest.mark.snapshot_needed(name=snapshot_microservices_build)
    @pytest.mark.revert_snapshot
    @pytest.mark.fail_snapshot
    @pytest.mark.usefixtures('k8s_installed')
    def test_fuel_ccp_build_images(self, env, cluster_roles):
        """Build images

        Scenario:
        1. Revert snapshot
        2. Upload microservices and ccpinstaller
        3. Create registry
        4. Build images
        5. Check calico network

        Duration 40 min
        """
        k8s_node = env.k8s_nodes[0]
        remote = env.node_ssh_client(
            k8s_node,
            **settings.SSH_NODE_CREDENTIALS)
        yaml_path = os.getcwd() + '/mcp_tests/templates/build-env.yaml'
        registry_pod = os.getcwd() + '/mcp_tests/templates/registry-pod.yaml'
        service_registry = os.getcwd() + '/mcp_tests' \
                                         '/templates/service-registry.yaml'
        exclude_list = ['deploy']
        with open(yaml_path, 'r') as yaml_path:
            params_list = yaml.load(yaml_path)['mcp-microservices-options']
            params = self.get_params(params_list, exclude_list)
            data = ' '.join(params)
            data = data.format(
                registry_address=cluster_roles['registry'],
                path_to_log=cluster_roles['path_to_log'],)
        command = [
            'kubectl create -f {0}'.format(registry_pod),
            'kubectl create -f {0}'.format(service_registry),
            'ccp {0}'.format(data)
        ]
        with remote.get_sudo(remote):
            for cmd in command:
                LOG.info(
                    "Running command '{cmd}' on node {node_name}".format(
                        cmd=cmd,
                        node_name=k8s_node.name
                    )
                )
                result = remote.execute(cmd)
                assert result['exit_code'] == 0
        remote.close()
        post_install_k8s_checks.check_calico_network(remote, env)

    @pytest.mark.snapshot_needed(name=snapshot_microservices_deployed)
    @pytest.mark.revert_snapshot(name=snapshot_microservices_build,
                                 strict=False)
    @pytest.mark.fail_snapshot
    @pytest.mark.namespace_name
    def test_fuel_ccp_deploy_microservices(
            self, env, k8sclient, cluster_roles):
        """Deploy base environment

        Scenario:
        1. Revert snapshot
        2. Upload microservices
        3. Deploy environment
        4. Label nodes
        5. Check deployment

        Duration 30 min
        """
        k8s_node = env.k8s_nodes[0]
        remote = env.node_ssh_client(
            k8s_node,
            **settings.SSH_NODE_CREDENTIALS)

        if remote.execute('which kubectl')['exit_code'] == 1:
            self.ccp_install_k8s(env, use_custom_yaml=True)
        exclude_list = ['build', '--builder-push', '--builder-workers 1']
        yaml_path = os.getcwd() + '/mcp_tests/templates/build-env.yaml'

        with open(yaml_path, 'r') as yaml_path:
            params_list = yaml.load(yaml_path)['mcp-microservices-options']
            params = self.get_params(params_list, exclude_list)
            data = ' '.join(params)
            data = data.format(
                registry_address=cluster_roles['registry'],
                images_namespace=cluster_roles['images_namespace'],
                images_tag=cluster_roles['images_tag'])
        command = [
            'ccp {0}'.format(data),
        ]
        kubectl_label_nodes = cluster_roles['kubectl_label_nodes']
        for label in kubectl_label_nodes:
            nodes = kubectl_label_nodes[label]
            node_str = ' '.join(nodes)
            cmd = 'kubectl label nodes {0} {1}=true'.format(node_str, label)
            command.append(cmd)
        with remote.get_sudo(remote):
            for cmd in command:
                LOG.info(
                    "Running command '{cmd}' on node {node_name}".format(
                        cmd=cmd,
                        node_name=k8s_node.name
                    )
                )
                result = remote.execute(cmd)
                assert result['exit_code'] == 0
        remote.close()
        post_os_deploy_checks.check_jobs_status(k8sclient)
        post_os_deploy_checks.check_pods_status(k8sclient)
