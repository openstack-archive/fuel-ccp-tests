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

import base_test
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests.helpers import post_os_deploy_checks
from fuel_ccp_tests.helpers import utils

LOG = logger.logger


class TestDeployTwoOS(base_test.SystemBaseTest):
    """Deploy Two OpenStack clusters with CCP

    """
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
    @pytest.mark.deploy_two_os
    @pytest.mark.fail_snapshot
    @pytest.mark.system
    def test_deploy_two_os(self, underlay, config, ccpcluster, k8s_actions):
        """Deploy base environment

        Scenario:
        1. Revert snapshot
        2. Install microservices
        3. Deploy one OS cluster
        4. Check deployment
        5. Create 2 vms
        6. Deploy another OS cluster
        7. Check deployment
        8. Create 2 vms

        Duration 90 min
        """
        if not settings.REGISTRY:
            k8s_actions.create_registry()
            ccpcluster.build()
        topology_path = \
            os.getcwd() + '/fuel_ccp_tests/templates/k8s_templates/' \
                          '1ctrl_1comp.yaml'
        remote = underlay.remote(host=config.k8s.kube_host)
        remote.upload(topology_path, '/tmp')
        utils.update_yaml(["deploy_config"], "/tmp/1ctrl_1comp.yaml",
                          yaml_file="./.ccp.yaml", remote=remote)
        underlay.sudo_check_call("pip install python-openstackclient",
                                 host=config.k8s.kube_host)
        ccpcluster.deploy()
        post_os_deploy_checks.check_jobs_status(k8s_actions.api, timeout=2000)
        post_os_deploy_checks.check_pods_status(k8s_actions.api)
        remote.check_call(
            "source openrc-{}; bash fuel-ccp/tools/deploy-test-vms.sh -a"
            " create".format(settings.CCP_CONF["kubernetes"]["namespace"]),
            timeout=600)

        topology_path = \
            os.getcwd() + '/fuel_ccp_tests/templates/k8s_templates/' \
                          '1ctrl_1comp_2.yaml'
        remote.upload(topology_path, '/tmp')
        utils.update_yaml(["deploy_config"], "/tmp/1ctrl_1comp_2.yaml",
                          yaml_file="./.ccp.yaml", remote=remote)
        utils.update_yaml(["kubernetes", "namespace"], "ccp-second",
                          yaml_file="./.ccp.yaml", remote=remote)
        ccpcluster.deploy()
        post_os_deploy_checks.check_jobs_status(k8s_actions.api, timeout=2000, namespace="ccp-second")
        post_os_deploy_checks.check_pods_status(k8s_actions.api, namespace="ccp-second")
        remote.check_call(
            "source openrc-ccp-second;"
            " bash fuel-ccp/tools/deploy-test-vms.sh -a create",
            timeout=600)
