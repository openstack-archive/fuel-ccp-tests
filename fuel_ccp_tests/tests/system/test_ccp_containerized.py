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

import base_test
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import post_os_deploy_checks

LOG = logger.logger


class TestCcpContainerized(base_test.SystemBaseTest):
    """Deploy OpenStack with CCP in container

       pytest.mark: ccp_containerized
    """

    @pytest.mark.ccp_containerized
    @pytest.mark.fail_snapshot
    def test_fuel_ccp_containerized(
            self, underlay, config, k8scluster, ccp_actions, show_step):
        """Deploy environment using ccp in container

        Scenario:
        1. Revert snapshot
        2. Install ccp in container
        3. Deploy environment
        4. Check deployment

        Duration 35 min
        """

        ccp_actions.default_params = settings.CCP_CLI_PARAMS
        show_step(2)
        ccp_actions.fetch_ccp()
        ccp_actions.dockerize_ccp()

        ccp_actions.put_yaml_config(
            path=settings.CCP_DEPLOY_CONFIG,
            config=settings.CCP_DEFAULT_GLOBALS)
        ccp_actions.put_yaml_config(
            path=settings.CCP_SOURCES_CONFIG,
            config=settings.CCP_BUILD_SOURCES)
        ccp_actions.put_yaml_config(
            path=settings.CCP_FETCH_CONFIG,
            config=settings.CCP_FETCH_PARAMS)

        with open(config.ccp_deploy.topology_path, 'r') as f:
            ccp_actions.put_raw_config(
                path=settings.CCP_DEPLOY_TOPOLOGY,
                content=f.read())

        ccp_actions.init_default_config(include_files=[
            settings.CCP_DEPLOY_CONFIG,
            settings.CCP_SOURCES_CONFIG,
            settings.CCP_DEPLOY_TOPOLOGY,
            settings.CCP_FETCH_CONFIG])
        config.ccp.os_host = config.k8s.kube_host

        if settings.REGISTRY == "127.0.0.1:31500":
            k8scluster.create_registry()
            ccp_actions.build()
        show_step(3)
        ccp_actions.deploy()
        post_os_deploy_checks.check_jobs_status(k8scluster.api)
        post_os_deploy_checks.check_pods_status(k8scluster.api)
        show_step(4)
        remote = underlay.remote(host=config.k8s.kube_host)
        underlay.sudo_check_call("pip install python-openstackclient",
                                 host=config.k8s.kube_host)
        remote.check_call(
            "source openrc-{0}; bash fuel-ccp/tools/deploy-test-vms.sh -k {0}"
            " -a create".format(
                settings.CCP_CONF["kubernetes"]["namespace"]),
            timeout=600)
