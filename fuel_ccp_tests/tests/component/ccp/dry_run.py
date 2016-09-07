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
from fuel_ccp_tests.helpers import ext

LOG = logger.logger


@pytest.mark.do_dry_run
@pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
class TestDryRun(object):
    """Deploy OpenStack from prebuilt yaml templates

       pytest.mark: do_dry_run
    """
    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
    @pytest.mark.fail_snapshot
    def test_fuel_ccp_dry_run(self, config, underlay, ccpcluster, k8scluster):
        """Deploy base environment

        Scenario:
        1. Revert snapshot
        2. Install microservices
        3. Create yaml templates
        4. Deploy environment
        4. Check deployment

        Duration 35 min
        """
        k8sclient = k8scluster.api
        k8scluster.create_registry()
        ccpcluster.build()
        export_dir = "/home/{user}/export".format(user=settings.SSH_LOGIN)
        ccpcluster.dry_deploy(export_dir=export_dir)
        k8scluster.create_objects(path=export_dir)
        post_os_deploy_checks.check_jobs_status(k8sclient, timeout=1500,
                                                namespace='default')
        post_os_deploy_checks.check_pods_status(k8sclient, timeout=2500,
                                                namespace='default')
