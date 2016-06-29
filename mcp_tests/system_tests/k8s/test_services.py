
import pytest

expected_services = ('kubernetes',)


@pytest.mark.parametrize('service', expected_services)
def test_exist_service(k8s_default_ns, service):
    k8s_default_ns.services.get(name=service)
