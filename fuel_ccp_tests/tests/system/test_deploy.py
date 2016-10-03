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
import json

import pytest
from junit_xml import TestSuite, TestCase

import base_test
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import post_os_deploy_checks
from fuel_ccp_tests.helpers import ext

LOG = logger.logger


class TestDeployOpenstack(base_test.SystemBaseTest):
    """Deploy OpenStack with CCP

       pytest.mark: deploy_openstack
    """

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
    @pytest.mark.deploy_openstack
    @pytest.mark.fail_snapshot
    @pytest.mark.smoke
    def test_fuel_ccp_deploy_microservices(
            self, underlay, config, ccpcluster, k8s_actions):
        """Deploy base environment

        Scenario:
        1. Revert snapshot
        2. Install microservices
        3. Deploy environment
        4. Check deployment

        Duration 35 min
        """
        if settings.BUILD_IMAGES:
            k8s_actions.create_registry()
            ccpcluster.build()
        else:
            if not settings.REGISTRY:
                raise ValueError("The REGISTRY variable should be set with "
                                 "external registry address, "
                                 "current value {0}".format(settings.REGISTRY))
        ccpcluster.deploy()
        post_os_deploy_checks.check_jobs_status(k8s_actions.api)
        post_os_deploy_checks.check_pods_status(k8s_actions.api)

        remote = underlay.remote(host=config.k8s.kube_host)
        underlay.sudo_check_call("pip install python-openstackclient",
                                 host=config.k8s.kube_host)
        remote.check_call(
            "source openrc-{}; bash fuel-ccp/tools/deploy-test-vms.sh -a"
            " create".format(settings.CCP_CONF["kubernetes"]["namespace"]),
            timeout=600)

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
    @pytest.mark.fail_snapshot
    @pytest.mark.openstack_tempest
    def test_deploy_openstack_run_tempest(self, underlay, config,
                                          ccpcluster, k8s_actions, rally):
        """Deploy base environment

        Scenario:
        1. Revert snapshot
        2. Install ccp
        3. Deploy environment
        4. Run tempest

        Duration 35 min
        """
        remote = underlay.remote(host=config.k8s.kube_host)
        if settings.BUILD_IMAGES:
            k8s_actions.create_registry()
            ccpcluster.build()
        else:
            if not settings.REGISTRY:
                raise ValueError("The REGISTRY variable should be set with "
                                 "external registry address, "
                                 "current value {0}".format(settings.REGISTRY))
        ccpcluster.deploy()
        post_os_deploy_checks.check_jobs_status(k8s_actions.api, timeout=4500)
        post_os_deploy_checks.check_pods_status(k8s_actions.api, timeout=4500)

        # prepare rally
        rally.prepare()
        rally.pull_image()
        rally.run()
        # run tempest
        rally.run_tempest()

        LOG.info('Storing tests results...')
        res_file_name = 'result.json'
        file_prefix = 'results_' + datetime.datetime.now().strftime(
            '%Y%m%d_%H%M%S') + '_'
        file_dst = '{0}/logs/{1}{2}'.format(
            settings.LOGS_DIR, file_prefix, res_file_name)
        remote.download(
            '/home/{0}/rally/{1}'.format(settings.SSH_LOGIN, res_file_name),
            file_dst)
        res = json.load(remote.open('/home/{}/rally/result.json'.format(
            settings.SSH_LOGIN)))
        formatted_tc = []
        failed_cases = [res['test_cases'][case]
                        for case in res['test_cases']
                        if res['test_cases'][case]['status']
                        in 'fail']
        for case in failed_cases:
            if case:
                tc = TestCase(case['name'])
                tc.add_failure_info(case['traceback'])
                formatted_tc.append(tc)

        skipped_cases = [res['test_cases'][case]
                         for case in res['test_cases']
                         if res['test_cases'][case]['status'] in 'skip']
        for case in skipped_cases:
            if case:
                tc = TestCase(case['name'])
                tc.add_skipped_info(case['reason'])
                formatted_tc.append(tc)

        error_cases = [res['test_cases'][case] for case in res['test_cases']
                       if res['test_cases'][case]['status'] in 'error']

        for case in error_cases:
            if case:
                tc = TestCase(case['name'])
                tc.add_error_info(case['traceback'])
                formatted_tc.append(tc)

        success = [res['test_cases'][case] for case in res['test_cases']
                   if res['test_cases'][case]['status'] in 'success']
        for case in success:
            if case:
                tc = TestCase(case['name'])
                formatted_tc.append(tc)

        ts = TestSuite("tempest", formatted_tc)
        with open('tempest.xml', 'w') as f:
            ts.to_file(f, [ts], prettyprint=False)
        fail_msg = 'Tempest verification fails {}'.format(res)
        assert res['failures'] == 0, fail_msg
