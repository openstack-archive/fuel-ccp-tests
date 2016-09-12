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
import os
import pytest
import requests

from fuel_ccp_tests.helpers import post_os_deploy_checks
from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests import settings


class TestPreStackLight(object):
    """TestPreCommitStackLight

    Scenario:
        1. Install k8s
        2. Install fuel-ccp
        3. Fetch all repositories
        4. Fetch stacklight from review
        5. Fetch repositories
        6. Build containers
        7. Deploy stack Light and openstack
        8. Run verification
    """

    kube_settings = {
        "hyperkube_image_repo": settings.HYPERKUBE_IMAGE_REPO,
        "hyperkube_image_tag": settings.HYPERKUBE_IMAGE_TAG,
        "upstream_dns_servers": settings.UPSTREAM_DNS,
        "nameservers": settings.NAMESERVERS,
        "searchdomains": settings.SEARCH_DOMAINS,
        "use_hyperkube_cni": str("true"),
    }
    
    @pytest.mark.test_stacklight_on_commit
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
    def test_deploy_os_with_custom_stack_light(
            self, ccpcluster, k8s_actions, underlay, config):
        """
        Scenario:
            1. Install k8s
        2. Install fuel-ccp
        3. Fetch all repositories
        4. Fetch stacklight from review
        5. Fetch repositories
        6. Build containers
        7. Deploy stack Light and openstack
        8. Run verification

        """

        remote = underlay.remote(host=config.k8s.kube_host)
        k8s_actions.create_registry()
        ccpcluster.fetch()
        ccpcluster.update_service('stacklight')
        ccpcluster.build(suppress_output=False)
        topology_path = os.getcwd() + '/fuel_ccp_tests/templates/' \
                                      'k8s_templates/stacklight_topology.yaml'

        remote.upload(topology_path, settings.CCP_CLI_PARAMS['deploy-config'])
        ccpcluster.deploy()
        post_os_deploy_checks.check_jobs_status(k8s_actions.api)
        post_os_deploy_checks.check_pods_status(k8s_actions.api)

        post_os_deploy_checks.check_pod_status_by_name(
            name='grafana',
            k8sclient=k8s_actions.api,
            namespace='ccp', count=None)

        post_os_deploy_checks.check_pod_status_by_name(
            name='stacklight-collector',
            k8sclient=k8s_actions.api,
            namespace='ccp', count=None)

        # get grafana port
        cmd = ("kubectl get service --namespace ccp grafana "
               "-o yaml | awk '/nodePort: / {print $NF}'")
        res = remote.execute(cmd)['stdout'][0].strip()
        grafana_port = ''.join(res)
        ip = config.k8s.kube_host

        # Auth in Grafana
        url = "http://{0}:{1}/api/org/".format(ip, grafana_port)

        res = requests.get(url,
                           auth=('admin', 'admin'))
        msg = "Grafana server responded with {0}, expected 200".format(
            res.status_code)
        assert (res.status_code, 200, msg)



