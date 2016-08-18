
import pytest

expected_namespaces = ('default', 'kube-system')


@pytest.mark.parametrize('ns', expected_namespaces)
def test_exist_namespace(k8scluster, ns):
    k8scluster.namespaces.get(name=ns)
