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
import json
import os
import pytest

from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests.helpers import post_os_deploy_checks


LOG = logger.logger
LOG.addHandler(logger.console)


class TestDeployTopology(object):

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.initial)
    @pytest.mark.deploy_controllers_only
    @pytest.mark.fail_snapshot
    def test_deploy_controlllers_only(self, config, underlay,
                                      k8scluster, ccpcluster):
        """Test deploy only controller nodes
        Scenario:
        1. Install k8s
        2. Install ccp
        3. Pull images
        4. Deploy only controller nodes
        5. Download test script
        6. Test services from controller

        Duration 60 min
        """
        k8sclient = k8scluster.get_k8sclient()

        remote = underlay.remote(host=config.k8s.kube_host)

        topology_path = os.getcwd() + '/fuel_ccp_tests/templates/' \
                                      'k8s_templates/single_controller_topology.yaml'
        remote.upload(topology_path, './')
        with remote.get_sudo(remote):
            ccpcluster.do_deploy(registry_address=settings.REGISTRY,
                                 deploy_config='~/k8s_topology.yaml',
                                 images_namespace=settings.IMAGES_NAMESPACE)
        post_os_deploy_checks.check_jobs_status(k8sclient, timeout=1500,
                                                namespace='ccp')
        post_os_deploy_checks.check_pods_status(k8sclient, timeout=2500,
                                                namespace='ccp')
        # TODO add check that config map cretaed only for services in topology

