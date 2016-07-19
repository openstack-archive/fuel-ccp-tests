import copy
import os
import subprocess

import pytest
import yaml

from mcp_tests import logger
from mcp_tests import settings
import base_test

LOG = logger.logger


class TestKargoDeployedEnv(base_test.SystemBaseTest):
    """Test class for testing environment deployed by Kargo"""

    kube_settings = {
        "kube_network_plugin": "calico",
        "kube_proxy_mode": "iptables",
        "kube_version": settings.KUBE_VERSION,
    }

    def deploy_kargo(self, env, use_custom_yaml=False):
        current_env = copy.deepcopy(os.environ)
        environment_variables = {
            "SLAVE_IPS": " ".join(env.k8s_ips),
            "ADMIN_IP": env.k8s_ips[0],
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
    @pytest.mark.revert_snapshot
    @pytest.mark.fail_snapshot
    @pytest.mark.usefixtures("kargo_deploy")
    def test_deployed_kargo(self, env, k8sclient):
        """Test for deploying an k8s environment and check it

        Scenario:
            1. Check number of nodes.
            2. Check running containers on nodes.
        """
        self.check_number_kube_nodes(env, k8sclient)
        self.check_running_containers(env)
