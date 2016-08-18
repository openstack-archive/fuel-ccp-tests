
import pytest

expected_services = ('kubernetes',)


@pytest.mark.parametrize('service', expected_services)
def test_exist_service(k8scluster, service):
    k8scluster.services.get(name=service)
