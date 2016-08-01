import pytest
import yaml
import base_test

from mcp_tests.helpers import checkers
from mcp_tests import logger
from mcp_tests import settings

LOG = logger.logger


@pytest.mark.usefixtures("prepare_env")
class TestDeployEnv(base_test.SystemBaseTest):
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
    def test_build_microservices(self, cluster_roles, env):
        """Build images

        Scenario:
        1. Revert snapshot
        2. Upload microservices and ccpinstaller
        3. Create registry
        4. Build images
        5. Check calico network

        Duration 40 min
        """
        master_node = env.k8s_nodes[0]
        remote = env.node_ssh_client(
            master_node,
            **settings.SSH_NODE_CREDENTIALS)

        yaml_path = cluster_roles['build_yaml']
        exclude_list = ['deploy']
        with open(yaml_path, 'r') as yaml_path:
            params_list = yaml.load(yaml_path)['mcp-microservices-options']
            params = self.get_params(params_list, exclude_list)
            data = ' '.join(params)
            data = data.format(
                registry_address=cluster_roles['registry'],
                path_to_log=cluster_roles['path_to_log'],
                path_to_conf=cluster_roles['path_to_conf'])
        command = [
            'kubectl create -f '
            '~/fuel-ccp-installer/registry/registry-pod.yaml',
            'kubectl create -f '
            '~/fuel-ccp-installer/registry/service-registry.yaml',
            'ccp {0}'.format(data)
        ]
        with remote.get_sudo(remote):
            for cmd in command:
                LOG.info(
                    "Running command '{cmd}' on node {node_name}".format(
                        cmd=cmd,
                        node_name=master_node.name
                    )
                )
                result = remote.execute(cmd)
                assert result['exit_code'] == 0
        remote.close()
        checkers.check_calico_network(remote, env)

    @pytest.mark.snapshot_needed(name=snapshot_microservices_deployed)
    @pytest.mark.revert_snapshot(name=snapshot_microservices_build,
                                 strict=False)
    @pytest.mark.fail_snapshot
    @pytest.mark.namespace_name
    def test_deploy_microservices(self, cluster_roles, env, k8sclient):
        """Deploy base environment

        Scenario:
        1. Revert snapshot
        2. Upload microservices
        3. Deploy environment
        4. Label nodes
        5. Check deployment

        Duration 30 min
        """
        master_node = env.k8s_nodes[0]
        remote = env.node_ssh_client(
            master_node,
            **settings.SSH_NODE_CREDENTIALS)

        if remote.execute('which kubectl')['exit_code'] == 1:
            self.ccp_install_k8s(env, use_custom_yaml=True)
        exclude_list = ['build', '--builder-push', '--builder-workers 1']
        yaml_path = cluster_roles['build_yaml']
        with open(yaml_path, 'r') as yaml_path:
            params_list = yaml.load(yaml_path)['mcp-microservices-options']
            params = self.get_params(params_list, exclude_list)
            data = ' '.join(params)
            data = data.format(
                registry_address=cluster_roles['registry'],
                path_to_log=cluster_roles['path_to_log'],
                path_to_conf=cluster_roles['path_to_conf'],
                images_namespace=cluster_roles['images_namespace'])
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
                        node_name=master_node.name
                    )
                )
                result = remote.execute(cmd)
                assert result['exit_code'] == 0

        remote.close()
        checkers.check_pods_status(k8sclient)
        checkers.check_jobs_status(k8sclient)
