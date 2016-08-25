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
from fuel_ccp_tests.helpers import post_install_k8s_checks
from fuel_ccp_tests.helpers import post_os_deploy_checks
from fuel_ccp_tests.helpers import ext

LOG = logger.logger


@pytest.mark.deploy_openstack
class TestDeployOpenstack(base_test.SystemBaseTest):
    """Deploy OpenStack with CCP

       pytest.mark: deploy_openstack
    """
    snapshot_microservices_deployed = 'snapshot_microservices_deployed'

    def get_params(self, params_list, exclude_list=None):
        params = []
        for item in params_list:
            if isinstance(item, dict):
                if item.keys()[0] not in exclude_list:
                    params.append(item)
            else:
                if item not in exclude_list:
                    params.append(item)
        params_dict = {}
        for item in filter(
                lambda x: isinstance(x, dict), params):
            params_dict.update(item)
        params_list = [item for item in params if not isinstance(
                       item, dict)]
        return params_list, params_dict

    def pre_build_deploy_step(self, remote):
        topology_path = os.path.join(
            os.getcwd(),
            'fuel_ccp_tests/templates/k8s_templates/k8s_topology.yaml')
        remote.upload(topology_path, './')
        command = '>/var/log/microservices.log'
        with remote.get_sudo(remote):
            LOG.info(
                "Running command '{cmd}' on node {node}".format(
                    cmd=command,
                    node=remote.hostname
                )
            )
            result = remote.check_call(command, verbose=True)
            assert result['exit_code'] == 0

    @pytest.mark.snapshot_needed(name=snapshot_microservices_deployed)
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.initial)
    @pytest.mark.fail_snapshot
    def test_fuel_ccp_deploy_microservices(self, config, underlay, ccpcluster,
                                           k8scluster):
        """Deploy base environment

        Scenario:
        1. Revert snapshot
        2. Install microservices
        3. Deploy environment
        4. Check deployment

        Duration 35 min
        """
        k8sclient = k8scluster.api
        remote = underlay.remote(host=config.k8s.kube_host)
        if settings.BUILD_IMAGES:
            k8scluster.create_registry()
            ccpcluster.build()
            post_install_k8s_checks.check_calico_network(remote, k8sclient)
        else:
            if not settings.REGISTRY:
                raise ValueError("The REGISTRY variable should be set with "
                                 "external registry address, "
                                 "current value {0}".format(settings.REGISTRY))
        ccpcluster.deploy()
        post_os_deploy_checks.check_jobs_status(k8sclient, timeout=1500,
                                                namespace='ccp')
        post_os_deploy_checks.check_pods_status(k8sclient, timeout=2500,
                                                namespace='ccp')
