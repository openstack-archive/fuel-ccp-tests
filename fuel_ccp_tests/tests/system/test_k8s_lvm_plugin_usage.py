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
from devops.helpers import ssh_client
import pytest

import base_test
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings

LOG = logger.logger


class TestLVMPluginUsage(base_test.SystemBaseTest):

    def get_remote(self, ip):
        ssh = ssh_client.SSHClient
        with ssh(ip, username=settings.SSH_LOGIN,
                 password=settings.SSH_PASSWORD) as remote:
            yield remote

    def check_lvm_exists(self, remote, lvm_name):
        LOG.info("Check if lvm storage exists")
        cmd = "lvs | grep {}".format(lvm_name)
        with remote.get_sudo(remote):
            self.exec_on_remote(remote, cmd)

    # TODO(slebedev): create test with nginx pod and checking lvm storage
    @pytest.mark.revert_snapshot
    @pytest.mark.usefixtures('enable_lvm_support')
    def test_create_nginx_with_lvm(self, k8scluster):
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
                ]
            }
        }
        k8sclient = k8scluster.get_k8sclient()
        pod = self.check_pod_create(body=nginx,
                                    k8sclient=k8sclient)
        remote = self.get_remote(pod.status.host_ip).next()
        self.check_lvm_exists(remote, lvm_volume_name)
        self.check_pod_delete(pod, k8sclient)
        self.check_lvm_exists(remote, lvm_volume_name)
