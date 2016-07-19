import copy
import os
import subprocess

import pytest
import yaml

from mcp_tests import logger
from mcp_tests import settings
from mcp_tests.system_tests import base_test

LOG = logger.logger


class TestKargoDeployedEnv(base_test.SystemBaseTest):
    """Test class for testing environment deployed by Kargo"""
    initial_snapshot = "empty"

    kube_settings = {
        "kube_network_plugin": "calico",
        "kube_proxy_mode": "iptables",
        "kube_version": settings.KUBE_VERSION,
    }

    def deploy_kargo(self, use_custom_yaml=False):
        current_env = copy.deepcopy(os.environ)
        environment_variables = {
            "SLAVE_IPS": " ".join(self.env.k8s_ips),
            "ADMIN_IP": self.env.k8s_ips[0],
        }
        if use_custom_yaml:
            environment_variables.update(
                {"CUSTOM_YAML": yaml.dump(
                    self.kube_settings, default_flow_style=False)}
            )
        current_env.update(dict=environment_variables)
        try:
            process = subprocess.Popen([settings.DEPLOY_SCRIPT],
                                       env=current_env,
                                       shell=True,
                                       bufsize=0,
                                       )
            assert process.wait() == 0
        except (SystemExit, KeyboardInterrupt) as err:
            process.terminate()
            raise err

    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(initial_snapshot)
    @pytest.mark.deploy_kargo(use_custom_yaml=True)
    @pytest.mark.fail_snapshot
    def test_deployed_kargo(self):
        """Test for deploying an k8s environment and check it

        Scenario:
            1. Create VMs using config from CONF_PATH system environment
            variable, or get an existing environment.
            2. Revert from initial snapshot to start deployment (if snapshot
            exists)
            3. Start deploying k8s via kargo_deploy.sh script, provided via
            DEPLOY_SCRIPT environment variable
            4. Check if nodes in k8s environment is equal to VMs nodes number.
            5. Check if all of base containers exists on k8s nodes.
        """
        self.check_number_kube_nodes()
        for node in self.env.k8s_nodes:
            self.running_containers(node)
