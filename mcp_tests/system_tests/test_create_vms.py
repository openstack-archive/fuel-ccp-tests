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

    env = envmanager.EnvironmentManager(settings.CONFIG_PATH)
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
    def test_upgrade_system_on_nodes(self):
        snapshot_name = self.upgraded_snapshot

        def upgrade(node):
            soft_requirements = [
                "git",
                "python-setuptools",
                "python-dev",
                "python-pip",
                "gcc",
                "libssl-dev",
                "libffi-dev",
                "vim",
                "software-properties-common"
            ]
            commands = [
                "apt-get update",
                "apt-get upgrade -y",
                "apt-get install -y {soft}".format(
                    soft=" ".join(soft_requirements)
                ),
                "apt-get autoremove -y",
                "pip install -U setuptools pip",
                "pip install 'cryptography>=1.3.2'",
                "pip install 'cffi>=1.6.0'"
            ]
            LOG.info("Getting ssh connect to {node_name}".format(
                node_name=node.name
            ))
            remote = self.env.node_ssh_client(
                node,
                **settings.SSH_NODE_CREDENTIALS
            )
            with remote.get_sudo(remote):
                for cmd in commands:
                    LOG.info(
                        "Running command '{cmd}' on node {node_name}".format(
                            cmd=cmd,
                            node_name=node.name
                        )
                    )
                    restart = True
                    while restart:
                        result = remote.execute(cmd)
                        if result['exit_code'] == 100:
                            # For some reasons dpkg may be locked by tasks
                            # for searching updates during login.
                            LOG.debug(
                                ("dpkg is locked on {node_name},"
                                 " another try in 5 secs").format(
                                     node_name=node.name))
                            time.sleep(5)
                            restart = True
                        else:
                            restart = False
                    assert result['exit_code'] == 0
            LOG.info("Closing connection to {}".format(node.name))
            remote.close()

        if not self.env.has_snapshot(snapshot_name):
            for node in self.env.k8s_nodes:
                upgrade(node)

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
            # "kube_version: \"v1.2.5\"",
        ]
        environment_variables = {
            "SLAVE_IPS": " ".join(self.env.k8s_ips),
            "ADMIN_IP": self.env.k8s_ips[0],
            "CUSTOM_YAML": "\n".join(kube_settings),
            "WORKSPACE": "/tmp",
        }
        current_env.update(dict=environment_variables)
        assert self.env.has_snapshot(self.upgraded_snapshot)
        self.env.revert_snapshot(self.upgraded_snapshot)
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

    @pytest.mark.skipif(not settings.SUSPEND_ENV_ON_TEARDOWN,
                        reason="Suspend isn't needed"
                        )
    @classmethod
    def teardown_class(cls):
        LOG.info("Suspending VMs")
        cls.env.suspend()
