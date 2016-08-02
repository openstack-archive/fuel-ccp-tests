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
        "hyperkube_image_repo": "gcr.io/google_containers/hyperkube",
        "hyperkube_image_tag": settings.KUBE_VERSION,
        "kube_version": settings.KUBE_VERSION,
        # Configure calico to set --nat-outgoing and --ipip pool option 18
        "ipip": settings.IPIP_USAGE,
        "docker_version": 1.12
    }

    # TODO(slebedev): create test with nginx pod and checking lvm storage
    @pytest.mark.revert_snapshot
    @pytest.mark.usefixtures('k8s_installed')
    @pytest.mark.usefixtures('env_lvm_support')
    def test_create_nginx_with_lvm(self, k8sclient):
        nginx = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": "nginx"
            },
            "spec": {
                "containers": [
                    {
                        "name": "nginx",
                        "image": "nginx",
                        "volumemounts": [
                            {
                                "mountPath": "/data",
                                "name": "test"
                            }
                        ],
                        "ports": [
                            {
                                "containerPort": 80
                            }
                        ]
                    }
                ],
                "volumes": [
                    {
                        "name": "test",
                        "flexVolume": {
                            "driver": "mirantis.com/lvm",
                            "fsType": "ext4",
                            "options": {
                                "volumeID": "vol1",
                                "size": "100m",
                                "pool": "pool",
                                "volumeGroup": "default"
                            }
                        }
                    }
                ]
            }
        }
        k8sclient.pods.create(body=nginx)
