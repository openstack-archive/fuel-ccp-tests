import copy
import os
import subprocess
import pytest
import time

from devops import error

from mcp_tests.managers import envmanager
from mcp_tests import logger
from mcp_tests import settings

LOG = logger.logger


class TestCreateEnv(object):
    """Create VMs for mcpinstaller"""

    env = envmanager.EnvironmentManager(settings.CONF_PATH)
    empty_snapshot = "empty"
    upgraded_snapshot = "upgraded"
    deployed_snapshot = "kargo_deployed"

    @classmethod
    def setup_class(cls):
        LOG.info("Creating environment")
        try:
            cls.env.get_env_by_name(name=settings.ENV_NAME)
        except error.DevopsObjNotFound:
            LOG.info("Environment doesn't exist, creating a new one")
            cls.env.create_environment()
            LOG.info("Environment created")

    @pytest.mark.create_vms
    def test_start_environment(self):
        snapshot_name = self.empty_snapshot
        LOG.info("Starting environment")
        self.env.start_environment()
        self.env.wait_ssh_k8s_nodes()
        if not self.env.has_snapshot(snapshot_name):
            self.env.create_snapshot(snapshot_name)
        else:
            self.env.revert_snapshot(snapshot_name)

    @pytest.mark.create_vms
    @pytest.mark.skipif(settings.DEPLOY_SCRIPT is None,
                        reason="Deploy script is not provided"
                        )
    def test_deploy_kargo(self):
        current_env = copy.deepcopy(os.environ)
        kube_settings = [
            "kube_network_plugin: \"calico\"",
            "kube_proxy_mode: \"iptables\"",
            "kube_version: \"{0}\"".format(settings.KUBE_VERSION),
        ]
        environment_variables = {
            "SLAVE_IPS": " ".join(self.env.k8s_ips),
            "ADMIN_IP": self.env.k8s_ips[0],
            "CUSTOM_YAML": "\n".join(kube_settings),
        }
        current_env.update(dict=environment_variables)
        assert self.env.has_snapshot(self.empty_snapshot)
        self.env.revert_snapshot(self.empty_snapshot)
        try:
            process = subprocess.Popen([settings.DEPLOY_SCRIPT],
                                       env=current_env,
                                       shell=True,
                                       bufsize=0,
                                       )
            assert process.wait() == 0
            self.env.create_snapshot(self.deployed_snapshot)
        except (SystemExit, KeyboardInterrupt) as err:
            process.terminate()
            raise err

    @pytest.mark.create_vms
    @pytest.mark.skipif(settings.DEPLOY_SCRIPT is None,
                        reason="Deploy script is not provided"
                        )
    def test_deploy_kargo_default(self):
        snapshot_name = self.empty_snapshot
        current_env = copy.deepcopy(os.environ)
        environment_variables = {
            "SLAVE_IPS": " ".join(self.env.k8s_ips),
            "ADMIN_IP": self.env.k8s_ips[0],
            "WORKSPACE": "/tmp",
        }
        current_env.update(dict=environment_variables)
        assert self.env.has_snapshot(snapshot_name)
        self.env.revert_snapshot(snapshot_name)
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

    @pytest.mark.skipif(not settings.SUSPEND_ENV_ON_TEARDOWN,
                        reason="Suspend isn't needed"
                        )
    @classmethod
    def teardown_class(cls):
        LOG.info("Suspending VMs")
        cls.env.suspend()
