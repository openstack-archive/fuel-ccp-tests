import pytest
import yaml

from mcp_tests.system_tests import base_test
from mcp_tests.helpers import checkers
from mcp_tests import logger
from mcp_tests import settings

LOG = logger.logger
import ipdb


@pytest.mark.usefixtures("prepare_env")
class TestDeployEnv(base_test.SystemBaseTest):
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
        "docker_options": settings.REGISTRY,
        "upstream_dns_servers": [settings.UPSTREAM_DNS],
    }

    @pytest.mark.snapshot_needed(name=snapshot_microservices_build)
    #@pytest.mark.revert_snapshot(name='test_deployed_kargo_passed')
    @pytest.mark.fail_snapshot
    @pytest.mark.parametrize('use_custom_yaml', [True])
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

        with open(yaml_path, 'r') as yaml_path:
            data = ' '.join(yaml.load(yaml_path)['mcp-microservices-options'])
            data = data.format(
                registry_address=cluster_roles['registry'],
                path_to_log=cluster_roles['path_to_log'],
                path_to_conf=cluster_roles['path_to_conf'])
        command = [
            'kubectl create -f '
            '~/fuel-ccp-installer/registry/registry-pod.yaml',
            'kubectl create -f '
            '~/fuel-ccp-installer/registry/service-registry.yaml',
            'ccp {0} build'.format(data)
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
    #@pytest.mark.revert_snapshot(name=snapshot_microservices_build)
    @pytest.mark.fail_snapshot
    @pytest.mark.parametrize('use_custom_yaml', [True])
    @pytest.mark.usefixtures('k8s_installed')
    def test_deploy_microservices(self, cluster_roles, env):
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

        yaml_path = cluster_roles['build_yaml']
        with open(yaml_path, 'r') as yaml_path:
            data = yaml.load(yaml_path)['mcp-microservices-options']
            data.remove(data[5])
            data = ' '.join(data)
            data = data.format(
                registry_address=cluster_roles['registry'],
                path_to_log=cluster_roles['path_to_log'],
                path_to_conf=cluster_roles['path_to_conf'])
        command = [
            'ccp {0} deploy'.format(data),
        ]
        kubectl_label_nodes = cluster_roles['kubectl_label_nodes']
        for label in kubectl_label_nodes:
            nodes = kubectl_label_nodes[label]
            node_str = ' '.join(nodes)
            cmd = 'kubectl label nodes {0} {1}=true'.format(node_str, label)
            command.append(cmd)
        ipdb.set_trace()
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
        checkers.check_pods_status(env)
        checkers.check_jobs_status(env)
