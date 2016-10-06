
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

from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import post_os_deploy_checks


LOG = logger.logger


class TestPreCommitEtcd(object):

    @pytest.mark.test_etcd_on_commit
    @pytest.mark.revert_snapshot(settings.PRECOMMIT_SNAPSHOT_NAME)
    def test_deploy_os_with_custom_etcd(
            self, ccpcluster, k8s_actions, config, underlay, show_step):
        """Precommit test for etcd
        :var SERVICE_PATH: path to fuel-ccp-mariadb repo

        Scenario:
        1. Install k8s
        2. Install fuel-ccp
        3. Upload all repositories
        4. Update etcd from review
        5. Build etcd container
        6. Deploy openstack
        7. Check etcd
        """
        if settings.BUILD_IMAGES:
            show_step(1)
            show_step(2)
            k8s_actions.create_registry()
            show_step(3)
            ccpcluster.fetch()
            show_step(4)
            ccpcluster.update_service('etcd')
            show_step(5)
            ccpcluster.build(suppress_output=False)
        else:
            if not settings.REGISTRY:
                raise ValueError("The REGISTRY variable should be set with "
                                 "external registry address, "
                                 "current value {0}".format(settings.REGISTRY))
        show_step(6)
        ccpcluster.deploy()
        post_os_deploy_checks.check_jobs_status(k8s_actions.api, timeout=2500)
        post_os_deploy_checks.check_pods_status(k8s_actions.api)

        show_step(7)
        remote = underlay.remote(host=config.k8s.kube_host)
        value = ['TEST', 'TEST_UPDATED']
        command = [
            'etcdctl set /message {0}'.format(value[0]),
            'etcdctl update /message {0}'.format(value[1])
        ]
        for cmd in command:
            LOG.info(
                "Running command '{cmd}' on node {node_name}".format(
                    cmd=command,
                    node_name=remote.hostname
                )
            )
            remote.check_call(cmd, verbose=True)

        cmd = 'etcdctl get /message'
        assert remote.check_call(cmd)['stdout_str'] == value[1], \
            "The value of key is not equal to {0}".format(value[1])
