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

import base_test
from mcp_tests import settings


class TestLVMPluginUsage(base_test.SystemBaseTest):

    kube_settings = {
        "kube_network_plugin": "calico",
        "kube_proxy_mode": "iptables",
        "hyperkube_image_repo": "quay.io/coreos/hyperkube",
        "hyperkube_image_tag": "{0}_coreos.0".format(settings.KUBE_VERSION),
        "kube_version": settings.KUBE_VERSION,
        # Configure calico to set --nat-outgoing and --ipip pool option 18
        "ipip": settings.IPIP_USAGE,
    }

    @pytest.mark.revert_snapshot
    @pytest.mark.usefixtures('k8s_installed')
    @pytest.mark.usefixtures('env_lvm_support')
    def test_test(self):
        pass
