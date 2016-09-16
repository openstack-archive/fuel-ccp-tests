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
import exceptions

from fuel_ccp_tests import logger
from fuel_ccp_tests.helpers import post_os_deploy_checks
from fuel_ccp_tests.helpers import ext

LOG = logger.logger


class TestPreCommitMariadb(object):
    """docstring for TestPreCommitMariadb
    """

    @pytest.mark.test_mariadb_on_commit
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
    def test_deploy_os_with_custom_mariadb(
            self, ccpcluster, k8s_actions, config, underlay):
        """Precommit test for mariadb

        Scenario:
        1. Install k8s
        2. Install fuel-ccp
        3. Fetch all repositories
        4. Fetch mariadb from review
        5. Fetch containers from external registry
        6. Build mariadb container
        7. Deploy openstack
        8. Check db
        """

        k8s_actions.create_registry()
        ccpcluster.fetch()
        ccpcluster.update_service('mariadb')
        ccpcluster.build(suppress_output=False)
        ccpcluster.deploy()

        post_os_deploy_checks.check_jobs_status(k8s_actions.api)
        post_os_deploy_checks.check_pods_status(k8s_actions.api)

        remote = underlay.remote(host=config.k8s.kube_host)
        LOG.info("Getting pod id")
        cmd = "kubectl get pods -lapp=mariadb --namespace=ccp"
        res_raw = remote.check_call(cmd)['stdout'][1]
        pod_id = [p_id for p_id in res_raw.split() if 'maria' in p_id][0]
        LOG.info("Pod ID is {0}".format(pod_id))
        cmd = "mysql  -uroot -ppassword -e 'SHOW DATABASES;'"
        pod_exec = \
            "kubectl exec -i {pod_id} --namespace=ccp -- {cmd}".format(
                pod_id=pod_id, cmd=cmd)
        result = remote.check_call(pod_exec)
        assert result['exit_code'] == 0, (
            'The command {0} exit code not equial to 0')
        base_tables = ['nova', 'keystone', 'neutron']
        result = [elem.rstrip() for elem in result['stdout']]
        for table in base_tables:
            if table not in result:
                raise exceptions.AssertionError(
                    'Table {0} is not in the list existing tables {1}'.format(
                        table, result))
