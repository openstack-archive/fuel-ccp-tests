import pytest

from mcp_tests import logger
from mcp_tests import settings
from mcp_tests.helpers import mcp_tests_exceptions
from mcp_tests.helpers.ssh_manager import SSHManager

LOG = logger.logger
LOG.addHandler(logger.console)


class ServiceBase(object):

    @pytest.fixture(autouse=True)
    def initialize_clients(self, env):
        self.ssh_manager = SSHManager()
        self.ssh_manager.initialize(
            env.k8s_ips[0],
            **settings.SSH_NODE_CREDENTIALS)

    def update_service(self, remote, service_name):
        if not settings.SERVICE_PATH:
            raise mcp_tests_exceptions.VariableNotSet('SERVICE_PATH')
        remote.execute(
            'rm -rf ./microservices-repos/fuel-ccp-{}'.format(service_name))
        remote.upload(
            settings.SERVICE_PATH,
            "./microservices-repos/")
