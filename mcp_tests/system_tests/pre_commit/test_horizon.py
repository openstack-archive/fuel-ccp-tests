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

from mcp_tests import logger
from mcp_tests import settings
from mcp_tests.helpers import post_os_deploy_checks
from mcp_tests.managers import k8s
from mcp_tests.managers import ccp
import base_test

LOG = logger.logger
LOG.addHandler(logger.console)


class TestServiceHorizon(base_test.ServiceBase):

    dockerfile = '''
    FROM {registry}/{tag}/horizon
    RUN apt-get install -y xvfb
    RUN apt-get install -y firefox-esr
    COPY local-horizon.conf \
     /horizon-master/openstack_dashboard/test/integration_tests
    '''.format(registry=settings.REGISTRY, tag='ccp')

    @pytest.mark.revert_snapshot
    @pytest.mark.horizon_test
    def test_horizon_component(self, env, k8sclient):
        """Horizon pre-commit test
        Scenario:
        1. Install k8s
        2. Install microservices
        3. Fetch all repos
        4. Update horizon source form local path
        5. Build images
        6. Deploy openstack
        7. Create directory to build horizon image for tests
        8. Upload config file for horizon tests
        9. Update horizon dashboard in config file
        10. Build docker image
        11. Run horizon tests from docker
        Duration 60 min
        """
        k8s.K8SManager.install_k8s(env)
        ccp.CCPManager.install_ccp(env)
        k8s_node = env.k8s_nodes[0]
        remote = env.node_ssh_client(
            k8s_node,
            **settings.SSH_NODE_CREDENTIALS)
        ccp.CCPManager.do_fetch(remote)
        self.update_service(remote, 'horizon')
        k8s.K8SManager.create_registry(remote)
        ccp.CCPManager.do_build(remote, 'builder_push',
                                registry_address=settings.REGISTRY)
        topology_path = os.getcwd() + '/mcp_tests/templates/' \
                                      'k8s_templates/k8s_topology.yaml'
        remote.upload(topology_path, './')
        ccp.CCPManager.do_deploy(remote,
                                 registry_address=settings.REGISTRY,
                                 deploy_config='~/k8s_topology.yaml')
        post_os_deploy_checks.check_jobs_status(k8sclient, timeout=1500,
                                                namespace='ccp')
        post_os_deploy_checks.check_pods_status(k8sclient, timeout=1500,
                                                namespace='ccp')
        # run horizon tests
        remote.execute("mkdir /tmp/horizon-tests")
        horizon_port = ''.join(remote.execute(
            "kubectl get service --namespace ccp horizon -o yaml |"
            " awk '/nodePort: / {print $NF}'")['stdout'])
        remote.upload(
            os.getcwd() + '/mcp_tests/templates/misc/local-horizon.conf',
            "/tmp/horizon-tests")
        remote.execute(
            r"sed -i '/dashboard_url=/c\dashboard_url=http://{0}:{1}'"
            r" /tmp/horizon-tests/local-horizon.conf".format(env.k8s_ips[0],
                                                             horizon_port))
        remote.execute(
            "echo -e '{}' >"
            " /tmp/horizon-tests/dockerfile".format(self.dockerfile))
        remote.execute(
            "docker build -t {}/horizon-test:test"
            " /tmp/horizon-tests/".format(settings.SSH_LOGIN))
        result = remote.execute(
            "docker run {}/horizon-test:test"
            " bash -c 'cd horizon-master;"
            " ./run_tests.sh -V'".format(settings.SSH_LOGIN))
        assert result['exit_code'] == 0,\
            "Horizon unit tests failed, result is {}".format(result)
