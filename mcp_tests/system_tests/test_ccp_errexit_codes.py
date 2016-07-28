
import pytest

from mcp_tests.managers import envmanager
from mcp_tests import settings


@pytest.yield_fixture(scope='session')
def admin_node(request):
    snapshot_name = 'kargo_deployed'
    env = envmanager.EnvironmentManager(settings.CONF_PATH)
    if env.has_snapshot(snapshot_name):
        env.revert_snapshot(snapshot_name)
    else:
        pytest.xfail("K8S didn't deploy. Snapshot {} is absent".format(
            snapshot_name))
    remote = env.node_ssh_client(
        env.k8s_nodes[0],
        user=settings.SSH_NODE_CREDENTIALS['login'],
        password=settings.SSH_NODE_CREDENTIALS['password'])
    yield remote
    remote.close()


class TestErrorInFetch(object):
    """docstring for TestErrorInFetch"""

    def test_wrong_repo_url(self, admin_node):
        cmd = ('ccp --repositories-fuel-ccp-debian-base '
               'http://example.org fetch')
        admin_node.check_call(cmd, expected=[1], verbose=True)

    def test_nonexistent_repo_name(self, ):
        cmd = 'ccp fetch --componets example'
        admin_node.check_call(cmd, expected=[1], verbose=True)


class TestErrorInBuild(object):
    """docstring for TestErrorInFetch"""

    def test_nonexistent_repo_name():
        cmd = 'ccp build --componets example'
        admin_node.check_call(cmd, expected=[1], verbose=True)

    def test_error_build_image():
        cmd = ('ccp fetch && '
               'echo "RUN exit 1" >> '
               '~/microservices-repos/fuel-ccp-debian-base/'
               'docker/base/Dockerfile.j2')
        cmd = 'ccp build --componets debian-base'
        admin_node.check_call(cmd, expected=[1], verbose=True)


class TestErrorInDeploy(object):
    """docstring for TestErrorInFetch"""

    def test_nonexistent_repo_name():
        cmd = 'ccp deploy --componets example'
        admin_node.check_call(cmd, expected=[1], verbose=True)
