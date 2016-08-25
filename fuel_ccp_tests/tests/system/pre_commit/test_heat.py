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
from fuel_ccp_tests.helpers import post_os_deploy_checks
from fuel_ccp_tests.helpers import ext

LOG = logger.logger
LOG.addHandler(logger.console)


@pytest.fixture(scope='function')
def ccp(ccp_actions, k8scluster):
    """Fixture initialize default params

    :param env_with_k8s: envmanager.EnvironmentManager

    """
    ccp_globals = settings.CCP_DEFAULT_GLOBALS
    ccp_actions.put_yaml_config(settings.CCP_CLI_PARAMS['deploy-config'],
                                ccp_globals)
    ccp_actions.default_params = settings.CCP_CLI_PARAMS
    ccp_actions.init_default_config()
    return ccp_actions


class TestDeployHeat(object):
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
    @pytest.mark.heat_component
    def test_heat_component(self, config, underlay,
                            k8scluster, ccpcluster, ccp, rally):
        """Heat pre-commit test
        Scenario:
        1. Fetch all repos
        2. Update heat source form local path
        3. Build images
        4. Deploy openstack
        5. check jobs are ready
        6. Check ppods are ready
        7. Run heat tests
        Duration 60 min
        """
        k8sclient = k8scluster.api
        remote = underlay.remote(host=config.k8s.kube_host)
        LOG.info('Fetch repositories...')
        ccpcluster.fetch()
        LOG.info('Update service...')
        ccpcluster.update_service('heat')
        LOG.info('Create registry')
        k8scluster.create_registry()
        LOG.info('Build images')
        ccpcluster.build()
        topology_path = os.getcwd() + '/fuel_ccp_tests/templates/' \
                                      'k8s_templates/k8s_topology.yaml'
        LOG.info('Upload topology')
        remote.upload(topology_path, settings.CCP_CLI_PARAMS['deploy-config'])
        LOG.info('Deploy services')
        ccpcluster.deploy()
        LOG.info('Check jobs are ready')
        post_os_deploy_checks.check_jobs_status(k8sclient, timeout=1500,
                                                namespace='ccp')
        LOG.info('Check pods are running')
        post_os_deploy_checks.check_pods_status(k8sclient, timeout=2500,
                                                namespace='ccp')
        rally.prepare()
        rally.pull_image()
        rally.run()
        rally.run_tempest('--regex tempest.api.orchestration')
