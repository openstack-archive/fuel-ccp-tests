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
import copy

import pytest

import base_test
from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings

LOG = logger.logger


@pytest.mark.system
class TestLCMScaleK8s(base_test.SystemBaseTest):
    """Test class for upgrade k8s by fuel-ccp-installer"""

    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    def test_lcm_k8s_upgrade(self, hardware, underlay, k8scluster):
        """Test for upgrade or rollback k8s components on a k8s environment

        Require:
         - already installed k8s cluster

        Scenario:
            1. Check that the k8s environment has expected
               component versions
            2. Run fuel-ccp-installer with updated custom_yaml
               for new components versions (higher or lower than it was)
            3. Check that the k8s environment has updated
               component versions
            4. Check number of kube nodes match underlay nodes.
            5. Check etcd health.
        """
        kube_settings = settings.DEFAULT_CUSTOM_YAML

        node_name = underlay.node_names()[0]  # instead of k8s master node

        # Make sure that the current deploy have expected versions
        self.check_required_versions(underlay, node_name, kube_settings)

        upgrade_to_kube_settings = copy.deepcopy(settings.DEFAULT_CUSTOM_YAML)
        upgrade_to_kube_settings.update({
            'kube_version': settings.UPGRADE_TO_KUBE_VERSION,
            'etcd_image_repo': settings.UPGRADE_TO_ETCD_IMAGE_REPO,
            'etcd_image_tag': settings.UPGRADE_TO_ETCD_IMAGE_TAG,
            'docker_version': settings.UPGRADE_TO_DOCKER_VERSION,
            'hyperkube_image_repo': settings.UPGRADE_TO_HYPERKUBE_IMAGE_REPO,
            'hyperkube_image_tag': settings.UPGRADE_TO_HYPERKUBE_IMAGE_TAG,
        })

        upgrade_msg = ''
        for key in kube_settings.keys():
            if kube_settings[key] != upgrade_to_kube_settings[key]:
                upgrade_msg += (
                    "*** Upgrade {0} from {1} to {2}\n"
                    .format(key, kube_settings[key],
                            upgrade_to_kube_settings[key])
                )
        assert upgrade_msg != '', "TestFailed please set UPGRADE_TO_* variable"
        LOG.info("Set for upgrade the following components:\n{}"
                 .format(upgrade_msg))
        k8scluster.install_k8s(custom_yaml=upgrade_to_kube_settings)

        # Check for expected versions after upgrade(rollback)
        self.check_required_versions(underlay, node_name,
                                     upgrade_to_kube_settings)

        # Perform some additional checks
        k8sclient = k8scluster.api
        self.check_number_kube_nodes(underlay, k8sclient)
        self.check_etcd_health(underlay)
