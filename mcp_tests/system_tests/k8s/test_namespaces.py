
import pytest

expected_namespaces = ('default', 'kube-system')


@pytest.mark.parametrize('ns', expected_namespaces)
def test_exist_namespace(k8s_default_ns, ns):
    k8s_default_ns.namespaces.get(name=ns)
