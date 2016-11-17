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
from fuel_ccp_tests.helpers import ext

LOG = logger.logger


@pytest.mark.component_k8s
class TestLVMPluginUsage(object):
    """Tests using k8s' LVM plugin.

    Required environment variables to use:
        CONF_PATH=./fuel-ccp-tests/templates/default-with-storage.yaml
        LVM_PLUGIN_PATH=/path/to/lvm/plugin

    To create basic pod node label 'lvm=on' is required on any k8s node.
    """

    def check_lvm_exists(self, remote, lvm_name):
        LOG.info("Check if lvm storage exists")
        cmd = "lvs | grep -w {}".format(lvm_name)
        with remote.get_sudo(remote):
            remote.check_call(command=cmd, verbose=True,
                              timeout=120)

    @pytest.mark.nginx_with_lvm
    def test_create_nginx_with_lvm(self, underlay, k8scluster):
        """Test creating pod with LVM plugin

        Scenario:
            1. Create nginx pod with LVM plugin usage on top of k8s.
            2. Ensure that volume is created.
            3. Delete pod.
            4. Ensure volume persists.
        """
        lvm_volume_group = "default"
        lvm_volume_name = "vol1"
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
                        "volumeMounts": [
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
                                "volumeID": lvm_volume_name,
                                "size": "100m",
                                "pool": "pool",
                                "volumeGroup": lvm_volume_group,
                            }
                        }
                    }
                ],
                "nodeSelector": {
                    "lvm": "on"
                }
            }
        }
        pod = k8scluster.check_pod_create(body=nginx)
        remote = underlay.remote(host=pod.status.host_ip)
        self.check_lvm_exists(remote, lvm_volume_name)
        k8scluster.check_pod_delete(pod)
        self.check_lvm_exists(remote, lvm_volume_name)
