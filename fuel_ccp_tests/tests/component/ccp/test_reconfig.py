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

import pytest

from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests.helpers import post_os_deploy_checks


LOG = logger.logger


@pytest.mark.ccp_cli_reconfig
@pytest.mark.ccp_cli_redeploy
@pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
@pytest.mark.component
def test_deploy_and_reconfig_keystone(config, ccpcluster,
                                      k8s_actions, underlay):

    ccpcluster.deploy()
    post_os_deploy_checks.check_jobs_status(k8s_actions.api)
    post_os_deploy_checks.check_pods_status(k8s_actions.api)

    remote = underlay.remote(host=config.k8s.kube_host)
    remote.execute('virtualenv ~/venv && '
                   'source ~/venv/bin/activate && '
                   'pip install python-openstackclient')
    res = remote.execute('source ~/venv/bin/activate ; '
                         'source ~/openrc-ccp; openstack user list -f json')
    LOG.debug("List of users {}".format(res.stdout_str))
    users1 = json.loads(res.stdout_str)
    remote.execute(
        "echo 'keystone__public_port: 5001' >> {deploy_config}".format(
            deploy_config=settings.DEPLOY_CONFIG))
    ccpcluster.deploy('keystone')
    post_os_deploy_checks.check_jobs_status(k8s_actions.api, timeout=2500)
    post_os_deploy_checks.check_pods_status(k8s_actions.api)

    res = remote.execute('source ~/venv/bin/activate ;'
                         'source ~/openrc-ccp; openstack user list -f json')
    LOG.debug("List of users {}".format(res.stdout_str))
    users2 = json.loads(res.stdout_str)

    remote.close()
    assert users1 == users2
