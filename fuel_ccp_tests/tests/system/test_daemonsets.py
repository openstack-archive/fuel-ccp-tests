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

import time

from devops.helpers import helpers
import pytest

from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests import logger

LOG = logger.logger


class TestDaemonsetsUpdates():
    """Test class for update DaemonSets"""

    from_nginx_image = 'nginx:1.10'
    to_nginx_image = 'nginx:1.11'

    def get_nginx_spec(self):
        """Create specification for DaemonSet with Nginx containers
            :return: nested dict
        """
        return {
            'apiVersion': 'extensions/v1beta1',
            'kind': 'DaemonSet',
            'metadata': {
                'labels': {'app': 'nginx'},
                'name': 'nginx',
            },
            'spec': {
                'template': {
                    'metadata': {
                        'labels': {'app': 'nginx'},
                        'name': 'nginx-app'},
                    'spec': {
                        'containers': [
                            {'name': 'nginx-app',
                             'image': self.from_nginx_image},
                        ],
                    },
                },
                'updateStrategy': {
                    'type': 'RollingUpdate',
                },
            }
        }

    def get_nginx_pods(self, k8sclient):
        """Return the nginx pods
            :param: k8sclient: kubernetes api client
            :return: list of pods with nginx containers
        """
        spec = self.get_nginx_spec()
        return [x for x in k8sclient.pods.list()
                if spec['metadata']['name'] in x.name]

    def get_nginx_ds(self, k8sclient):
        """Return the nginx DaemonSets
            :param k8sclient: kubernetes api client
            :return: list of DaemonSets with pods with nginx containers
        """
        spec = self.get_nginx_spec()
        return [x for x in k8sclient.daemonsets.list()
                if spec['metadata']['name'] in x.name]

    def wait_nginx_pods_ready(self, k8sclient):
        """Wait until the nginx pods are ready
            :param: k8sclient: kubernetes api client
            :return: None
        """
        nginx_pods = self.get_nginx_pods(k8sclient)
        for pod in nginx_pods:
            pod.wait_running(timeout=60)

    def delete_nginx_pods(self, k8sclient):
        """Delete the nginx pods
            :param: k8sclient: kubernetes api client
            :return: None
        """
        nginx_pods = self.get_nginx_pods(k8sclient)
        for pod in nginx_pods:
            k8sclient.pods.delete(body=pod.spec, name=pod.name)
            helpers.wait(lambda: pod.name not in [
                x.name for x in self.get_nginx_pods(k8sclient)])

    def check_nginx_pods_image(self, k8sclient, nginx_image):
        """Check nginx pods image version
            :param: k8sclient: kubernetes api client,
            :param: nginx_image: version of nginx_image to compare
            :return: None
        """
        nginx_pods = self.get_nginx_pods(k8sclient)
        for pod in nginx_pods:
            pod_image = pod.status.container_statuses[0].image
            assert pod_image == nginx_image, (
                "Pod {0} has image {1} while expected {2}"
                .format(pod.name, pod_image, nginx_image))

    def check_nginx_ds_image(self, k8sclient, nginx_image):
        """Check nginx DaemonSets version
            :param: k8sclient: kubernetes api client,
            :param: nginx_image: version of nginx_image to compare
            :return: None
        """
        nginx_daemonsets = self.get_nginx_ds(k8sclient)
        for nginx_ds in nginx_daemonsets:
            nginx_ds_image = nginx_ds.spec.template.spec.containers[0].image
            assert nginx_ds_image == nginx_image, (
                "DaemonSet {0} has image {1} while expected {2}"
                .format(nginx_ds.name, nginx_ds_image, nginx_image))

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_rollingupdate_noop(self, k8scluster, show_step):
        """Update a daemonset using updateStrategy type: Noop

        Scenario:
            1. Deploy k8s using fuel-ccp-installer
            2. Create a DaemonSet for nginx with image version 1_10 and
               update strategy Noop
            3. Wait until nginx pods are created and become 'ready'
            4. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            5. Change nginx image version to 1_11 using YAML
            6. Wait for 10 seconds (needs to check that there were
               no auto updates of the nginx pods)
            7. Check that the image version in the nginx pods is still 1_10
               Check that the image version in the nginx daemonset
               is updated to 1_11
            8. Kill all nginx pods that are belong to the nginx daemonset
            9. Wait until nginx pods are created and become 'ready'
           10. Check that the image version in the nginx pods
               is updated to 1_11

        Duration: 3000 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8scluster.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        nginx_spec = self.get_nginx_spec()
        nginx_spec['spec']['updateStrategy']['type'] = 'Noop'
        nginx_spec['spec']['template']['spec']['containers'][0][
            'image'] = self.from_nginx_image
        k8sclient.daemonsets.create(body=nginx_spec)

        # STEP #3
        show_step(3)
        time.sleep(3)
        self.wait_nginx_pods_ready(k8sclient)

        # STEP #4
        show_step(4)
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)

        # STEP #5
        show_step(5)
        nginx_spec['spec']['template']['spec']['containers'][0][
            'image'] = self.to_nginx_image
        k8sclient.daemonsets.update(body=nginx_spec,
                                    name=nginx_spec['metadata']['name'])

        # STEP #6
        show_step(6)
        time.sleep(10)

        # STEP #7
        show_step(7)
        # Pods should still have the old image version
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)
        # DaemonSet should have new image version
        self.check_nginx_ds_image(k8sclient, self.to_nginx_image)

        # STEP #8
        show_step(8)
        self.delete_nginx_pods(k8sclient)

        # STEP #9
        show_step(9)
        self.wait_nginx_pods_ready(k8sclient)

        # STEP #10
        show_step(10)
        # Pods should have the new image version
        self.check_nginx_pods_image(k8sclient, self.to_nginx_image)

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_rollingupdate(self, k8scluster, show_step):
        """Update a daemonset using updateStrategy type: RollingUpdate

        Scenario:
            1. Deploy k8s using fuel-ccp-installer
            2. Create a DaemonSet for nginx with image version 1_10 and
               update strategy RollingUpdate
            3. Wait until nginx pods are created and become 'ready'
            4. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            5. Change nginx image version to 1_11 using YAML
            6. Check that the image version in the nginx daemonset
               is updated to 1.11 .
               Wait for ~120 sec that the image version in the nginx pods
               is changed to 1.11 .

        Duration: 3000 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8scluster.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        nginx_spec = self.get_nginx_spec()
        nginx_spec['spec']['template']['spec']['containers'][0][
            'image'] = self.from_nginx_image
        k8sclient.daemonsets.create(body=nginx_spec)

        # STEP #3
        show_step(3)
        time.sleep(3)
        self.wait_nginx_pods_ready(k8sclient)

        # STEP #4
        show_step(4)
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)

        # STEP #5
        show_step(5)
        nginx_spec['spec']['template']['spec']['containers'][0][
            'image'] = self.to_nginx_image
        k8sclient.daemonsets.update(body=nginx_spec,
                                    name=nginx_spec['metadata']['name'])

        # STEP #6
        show_step(6)
        # DaemonSet should have new image version
        self.check_nginx_ds_image(k8sclient, self.to_nginx_image)
        # Pods should have new image version
        helpers.wait(lambda: self.check_nginx_pods_image(k8sclient,
                                                         self.to_nginx_image),
                     timeout=2 * 60,
                     timeout_msg="Image on pods is not updated")

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_rollout_rollingupdate(self, underlay,
                                             k8scluster, config, show_step):
        """Update a daemonset using updateStrategy type: RollingUpdate

        Scenario:
            1. Deploy k8s using fuel-ccp-installer
            2. Create a DaemonSet for nginx with image version 1_10 and
               update strategy RollingUpdate
            3. Wait until nginx pods are created and become 'ready'
            4. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            5. Change nginx image version to 1_11 using YAML
            6. Wait for 10 seconds (needs to check that there were
               no auto updates of the nginx pods)
            7. Check that the image version in the nginx daemonset
               is updated to 1.11 .
               Wait for ~120 sec that the image version in the nginx pods
               is changed to 1.11 .
            8. Rollback the nginx daemonset:
               kubectl rollout undo daemonset/nginx
            9. Check that the image version in the nginx daemonset is
                downgraded to 1.10 .
               Wait for ~120 sec that the image version in the nginx pods
                is downgraded to 1.10

        Duration: 3000 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8scluster.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        nginx_spec = self.get_nginx_spec()
        nginx_spec['spec']['template']['spec']['containers'][0][
            'image'] = self.from_nginx_image
        k8sclient.daemonsets.create(body=nginx_spec)

        # STEP #3
        show_step(3)
        time.sleep(3)
        self.wait_nginx_pods_ready(k8sclient)

        # STEP #4
        show_step(4)
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)

        # STEP #5
        show_step(5)
        nginx_spec['spec']['template']['spec']['containers'][0][
            'image'] = self.to_nginx_image
        k8sclient.daemonsets.update(body=nginx_spec,
                                    name=nginx_spec['metadata']['name'])

        # STEP #6
        show_step(6)
        time.sleep(10)

        # STEP #7
        show_step(7)
        # DaemonSet should have new image version
        self.check_nginx_ds_image(k8sclient, self.to_nginx_image)
        # Pods should have new image version
        helpers.wait_pass(
            lambda: self.check_nginx_pods_image(
                k8sclient,
                self.to_nginx_image),
            timeout=2 * 60
        )
        # STEP #8
        show_step(8)
        cmd = "kubectl rollout undo daemonset/nginx"
        underlay.check_call(cmd,
                            host=config.k8s.kube_host)

        # STEP #9
        show_step(9)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)
        # Pods should have new image version
        helpers.wait_pass(
            lambda: self.check_nginx_pods_image(
                k8sclient,
                self.from_nginx_image),
            timeout=2 * 60
        )
