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

from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests.helpers import post_os_deploy_checks


LOG = logger.logger
LOG.addHandler(logger.console)


class Teststacklight(object):

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.initial)
    @pytest.mark.pre_commit_stack_light
    @pytest.mark.fail_snapshot
    def test_build_deploy_stack_light(self, config, underlay,
                                      k8scluster, ccpcluster):
        """Test build, deploy and stack light service
        Scenario:
        1. Fetch all repositories and update stack light
        2. Create internal registry
        3. Build images and push into registry
        4. Deploy services
        5. Check jobs are success
        6. Check pods are running
        7. TBD: add stack light checkers

        Duration 60 min
        """
        k8sclient = k8scluster.get_k8sclient()

        remote = underlay.remote(host=config.k8s.kube_host)
        # Fetch all repositories
        ccpcluster.do_fetch()
        # Update stacklight
        ccpcluster.update_service('stacklight')
        # create registry
        k8scluster.create_registry(remote)
        # build and push images
        ccpcluster.do_build('builder_push',
                            registry_address=settings.REGISTRY)
        topology_path = os.getcwd() + '/fuel_ccp_tests/templates/' \
                                      'k8s_templates/k8s_topology.yaml'
        remote.upload(topology_path, './')
        with remote.get_sudo(remote):
            # deploy
            ccpcluster.do_deploy(registry_address=settings.REGISTRY,
                                 deploy_config='~/k8s_topology.yaml',
                                 )
        # Check jobs are success
        post_os_deploy_checks.check_jobs_status(k8sclient, timeout=1500,
                                                namespace='ccp')
        # Check pods are success
        post_os_deploy_checks.check_pods_status(k8sclient, timeout=2500,
                                                namespace='ccp')
        # TODO (tleontovich) Add checkers for stack light
