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
import datetime
import pytest

from fuel_ccp_tests.helpers import post_os_deploy_checks
from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings

LOG = logger.logger
LOG.addHandler(logger.console)


class TestPreCommitNeutron(object):
    """docstring for TestPreCommitNeutron

    Scenario:
        1. Install k8s
        2. Install fuel-ccp
        3. Fetch all repositories
        4. Fetch neutron from review
        5. Fetch containers from external registry
        6. Build neutron container
        7. Deploy Openstack
        8. Run tempest
    """

    @pytest.mark.test_neutron_on_commit
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
    def test_deploy_os_with_custom_neutron(
            self, ccpcluster, k8s_actions, rally, underlay, config):
        """
        Scenario:
            1. Install k8s
            2. Install fuel-ccp
            3. Fetch repos
            4. Upload repo with changes
            5. Build components
            6. Deploy components
            7. Run tempest suite

        """
        remote = underlay.remote(host=config.k8s.kube_host)
        k8s_actions.create_registry()
        ccpcluster.fetch()
        ccpcluster.update_service('neutron')
        ccpcluster.build(suppress_output=False)
        ccpcluster.deploy()
        rally.prepare()
        rally.pull_image()
        rally.run()

        post_os_deploy_checks.check_jobs_status(k8s_actions.api)
        post_os_deploy_checks.check_pods_status(k8s_actions.api)
        rally.run_tempest('--regex  tempest.api.network')
        LOG.info('Storing tests results...')
        res_file_name = 'result.html'
        file_prefix = 'results_' + datetime.datetime.now().strftime(
            '%Y%m%d_%H%M%S') + '_'
        file_dst = '{0}/logs/{1}{2}'.format(
            settings.LOGS_DIR, file_prefix, res_file_name)
        remote.download(
            '/home/{0}/rally/{1}'.format(settings.SSH_LOGIN, res_file_name),
            file_dst)
        import json
        res = json.load(remote.open('/home/vagrant/rally/result.json'))

        fail_msg = 'Tempest verification fails {}'.format(res)
        assert res['failures'] == 0, fail_msg
