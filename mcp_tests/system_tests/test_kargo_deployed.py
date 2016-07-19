import pytest

from mcp_tests import logger
from mcp_tests import system_tests

LOG = logger.logger


class TestKargoDeployedEnv(system_tests.SystemBaseTest):

    initial_snapshot = "empty"

    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(initial_snapshot)
    @pytest.mark.deploy_kargo(use_custom_yaml=True)
    @pytest.mark.fail_snapshot
    def test_deployed_kargo(self):
        self.check_number_kube_nodes()
        for node in self.env.k8s_nodes:
            self.running_containers(node)
