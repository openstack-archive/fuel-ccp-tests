
import pytest
from mcp_tests import settings
from mcp_tests.models.k8s import K8sCluster


@pytest.fixture(scope='session')
def k8s_default_ns(request):
    user = settings.KUBE_ADMIN_USER
    password = settings.KUBE_ADMIN_PASS
    host = settings.KUBE_HOST
    return K8sCluster(user=user, password=password,
                      host=host, namespace='default')
