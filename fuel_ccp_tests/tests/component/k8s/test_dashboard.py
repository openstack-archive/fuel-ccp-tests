#    Copyright 2016 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import pytest

from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests import logger

LOG = logger.logger


@pytest.mark.k8s_dashboard
class TestK8sDashboard(object):

    kube_settings = {
        "hyperkube_image_repo":
        "artifactory.mcp.mirantis.net:5002/hyperkube-amd64",
        "hyperkube_image_tag": "v1.4.0-beta.0-1-gd80ff_64",
        "upstream_dns_servers": ["172.18.80.135", "172.18.16.10"],
        "nameservers": ["8.8.8.8", "172.18.80.136"],
        "searchdomains": ["ccp.svc.cluster.local", "mcp.mirantis.net",
                          "mirantis.net"],
        "use_hyperkube_cni": str("true"),
    }

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    @pytest.mark.dashboard_exists
    def test_k8s_dashboard_exists(self, k8scluster):
        k8sclient = k8scluster.api
        LOG.info("Check if dashboard service exists")
        assert k8sclient.services.get(
            name="kubernetes-dashboard",
            namespace="kube-system") is not None, "Dashboard service is missed"
        LOG.info("Check if dashboard endpoint exists")
        dashboard_endpoint = k8sclient.endpoints.get(
            name="kubernetes-dashboard",
            namespace="kube-system")
        assert dashboard_endpoint is not None, "Dashboard endpoint is missing"
        LOG.info("Check if dashboard pods are running")
        for subset in dashboard_endpoint.subsets:
            for address in subset.addresses:
                assert k8sclient.pods.get(
                    name=address.target_ref.name,
                    namespace=address.target_ref.namespace
                ).phase == "Running", "Pod is not Running phase!"

