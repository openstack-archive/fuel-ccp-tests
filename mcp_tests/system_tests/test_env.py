import pytest

from mcp_tests import logger
from mcp_tests.managers import envmanager
from mcp_tests import settings
from mcp_tests import system_tests

LOG = logger.logger


@pytest.mark.skipif(settings.ENV_NAME is None,
                    reason="Skip of missed images")
class TestDeployedEnv(system_tests.SystemBaseTest):
    """Basis test case for testing an existing environment

    Scenario:
        1. Get an existing environment (from setup_class of parent class)
        2. Resume VMs for testing
        3. Determine master ips (if exists)
        4. Determine slaves ips
        5. Check if ssh to each node could be get
        6. Compare number of slaves with k8s' nodes number
        7. Check if all base containers exist on nodes
        8. Suspend VMs.
    """
    env = envmanager.EnvironmentManager(
        config_file=settings.CONF_PATH)
    base_images = [
        "calico/node",
        "andyshinn/dnsmasq",
        "quay.io/smana/kubernetes-hyperkube"
    ]

    def running_containers(self, node):
        """Check if there are all base containers on node

        :param node: devops.models.Node
        """
        remote = self.env.node_ssh_client(
            node,
            **settings.SSH_NODE_CREDENTIALS
        )
        cmd = "docker ps --no-trunc --format '{{.Image}}'"
        with remote.get_sudo(remote):
            result = remote.execute(
                command=cmd,
                verbose=True
            )
            assert result['exit_code'] == 0
        images = [x.split(":")[0] for x in result['stdout']]
        assert set(self.base_images) < set(images)

    @pytest.mark.env_base
    def test_resume_vms(self):
        """Resume Environment"""
        LOG.info("Trying to resume environment")
        self.env.resume()
        self.env.start_environment()

    @pytest.mark.xfail
    @pytest.mark.env_base
    def test_get_master_ips(self):
        """Trying to determine master nodes ips"""
        LOG.info("Trying to get master ips")
        ips = self.env.admin_ips
        LOG.debug("Master IPs: {0}".format(ips))
        assert ips is not None and len(ips) > 0

    @pytest.mark.xfail
    @pytest.mark.env_base
    def test_get_slaves_ips(self):
        """Trying to determine slave nodes ips"""
        LOG.info("Trying to get slave ips")
        ips = self.env.slave_ips
        LOG.debug("Slave IPs: {0}".format(ips))
        assert ips is not None and len(ips) > 0

    @pytest.mark.env_base
    def test_get_k8s_ips(self):
        LOG.info("Trying to get k8s ips")
        ips = self.env.k8s_ips
        LOG.debug("K8S IPs: {0}".format(ips))
        assert ips is not None and len(ips) > 0

    @pytest.mark.env_base
    def test_get_node_ssh(self):
        """Try to get remote client for each node"""
        LOG.info("Get remote for each master node")
        for node in self.env.master_nodes:
            remote = self.env.node_ssh_client(
                node, **settings.SSH_NODE_CREDENTIALS)
            assert remote is not None

        LOG.info("Get remote for each slave node")
        for node in self.env.slave_nodes:
            remote = self.env.node_ssh_client(
                node, **settings.SSH_NODE_CREDENTIALS)
            assert remote is not None

        LOG.info("Get remote for each k8s node")
        for node in self.env.k8s_nodes:
            remote = self.env.node_ssh_client(
                node, **settings.SSH_NODE_CREDENTIALS
            )
            assert remote is not None

    @pytest.mark.env_base
    def test_kube_nodes_number_the_same(self):
        """Check number of slaves"""
        LOG.info("Check number of nodes")
        master = self.env.k8s_nodes[0]
        remote = self.env.node_ssh_client(
            master,
            **settings.SSH_NODE_CREDENTIALS
        )
        cmd = "kubectl get nodes -o jsonpath={.items[*].metadata.name}"
        result = remote.execute(command=cmd, verbose=True)
        assert result["exit_code"] == 0, "Error: {0}".format(
            "".join(result.stderr)
        )
        k8s_nodes = result["stdout_str"].split()
        devops_nodes = self.env.k8s_nodes
        assert len(k8s_nodes) == len(devops_nodes)

    @pytest.mark.env_base
    def test_base_container_exists(self):
        """Check if all of base container exists"""
        LOG.info("Checking docker container exists")
        for node in self.env.k8s_nodes:
            self.running_containers(node)
