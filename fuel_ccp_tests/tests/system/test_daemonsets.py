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
import pytest

from devops.helpers import helpers

import base_test
from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests import logger


LOG = logger.logger


class TestDaemonsetsUpdates(base_test.SystemBaseTest):
    """Test class for update DaemonSets"""

    from_nginx_image = 'nginx:1.10'
    to_nginx_image = 'nginx:1.11'
    to_nginx_image_1_12 = 'nginx:1.12'

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

    def check_nginx_revision_image(self, config, underlay,
                                   revision, nginx_image):
        cmd = "kubectl rollout history daemonset/nginx " \
              "--revision {} | grep Image".format(revision)
        nginx_revision_image = underlay.check_call(cmd,
                                                   host=config
                                                   )['stdout_str'].replace(
            '\t', '').split(
            ":", 1)[1]
        assert nginx_revision_image == nginx_image, (
            "revision {0} has image {1} while expected {2}".format(
                revision, nginx_revision_image, nginx_image))

    def get_nginx_pod_start_time(self, k8sclient):
        start_time = {}
        for pod in self.get_nginx_pods(k8sclient):
            start_time[pod.name] = pod.status._container_statuses[
                0].state.running.started_at
        return start_time

    def check_rollout_skipping(self, k8sclient,
                               config, underlay, revision=None):

        # collect pods start time
        start_time = self.get_nginx_pod_start_time(k8sclient)

        # try to rollout
        if revision:
            cmd = "kubectl rollout undo daemonset/nginx --to-revision=0"
        else:
            cmd = "kubectl rollout undo daemonset/nginx"
        stdout = underlay.check_call(cmd, host=config)['stdout_str']
        warning_message = 'daemonset "nginx" skipped rollback ' \
                          '(DaemonRollbackRevisionNotFound: ' \
                          'Unable to find last revision.)'
        assert stdout == warning_message, (
            "wrong warning message: \n{}. Expected: \n{}".format(
                stdout, warning_message))

        # check that pods start time don't changed
        # collect pods start time
        start_time_after_rollout = self.get_nginx_pod_start_time(k8sclient)

        assert start_time == start_time_after_rollout, (
            "pod's restarted. pods start time before rollout: \n{}\n "
            "pods start time after rollout: \n{}".format(
                start_time,
                start_time_after_rollout)
        )

    def create_daemonset(self, nginx_spec, k8sclient, noop=None):
        if noop:
            nginx_spec['spec']['updateStrategy']['type'] = 'Noop'
        nginx_spec['spec']['template']['spec']['containers'][0][
            'image'] = self.from_nginx_image
        k8sclient.daemonsets.create(body=nginx_spec)

    @staticmethod
    def update_daemonset(nginx_spec, k8sclient, nginx_image):
        nginx_spec['spec']['template']['spec']['containers'][0][
            'image'] = nginx_image
        k8sclient.daemonsets.update(body=nginx_spec,
                                    name=nginx_spec['metadata']['name'])

    @staticmethod
    def rollout_daemonset(underlay, config, revision=None):
        if revision:
            cmd = "kubectl rollout undo " \
                  "daemonset/nginx --to-revision={}".format(revision)
        else:
            cmd = "kubectl rollout undo daemonset/nginx"
        underlay.check_call(cmd,
                            host=config.k8s.kube_host)

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
        self.create_daemonset(nginx_spec, k8sclient, noop=True)

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
        self.update_daemonset(nginx_spec, k8sclient, self.to_nginx_image)

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
            6. Wait for 10 seconds (needs to check that there were
               no auto updates of the nginx pods)
            7. Check that the image version in the nginx daemonset
               is updated to 1_11
               Wait for ~120 sec that the image version in the nginx pods
               is changed to 1_11

        Duration: 3000 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8scluster.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        nginx_spec = self.get_nginx_spec()
        self.create_daemonset(nginx_spec, k8sclient)

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
        self.update_daemonset(nginx_spec, k8sclient, self.to_nginx_image)

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
            timeout=2 * 60)

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_rollout_rollingupdate(self, underlay,
                                             k8scluster, config, show_step):
        """Rollback a daemonset using updateStrategy type: RollingUpdate

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
               is updated to 1_11
               Wait for ~120 sec that the image version
               in the nginx pods is changed to 1_11
            8. Rollback the nginx daemonset:
               kubectl rollout undo daemonset/nginx
            9. Check that the image version in the nginx daemonset is
               downgraded to 1_10
               Wait for ~120 sec that the image version
               in the nginx pods is downgraded to 1_10

        Duration: 3000 seconds
        """

        self.test_daemonset_rollingupdate(k8scluster, show_step)

        k8sclient = k8scluster.api

        show_step(8)
        self.rollout_daemonset(underlay, config)

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

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_rollout_noop(self, underlay,
                                    k8scluster, config, show_step):
        """Rollback a daemonset using updateStrategy type: Noop

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
           11. Rollout the daemonset to a previous revision:
                kubectl rollout undo daemonset/nginx
           12. Check that the image version in the nginx pods is still 1_11
               Check that the image version in the nginx daemonset
               is changed to 1_10
           13. Kill all nginx pods that are belong to the nginx daemonset
           14. Wait until nginx pods are created and become 'ready'
           15. Check that the image version in the nginx pods
               is changed to 1_10


        Duration: 3000 seconds
        """

        self.test_daemonset_rollingupdate_noop(k8scluster, show_step)

        k8sclient = k8scluster.api

        # STEP #11
        show_step(11)
        self.rollout_daemonset(underlay, config)

        # STEP #12
        show_step(12)
        # Pods should still have the new image version
        self.check_nginx_pods_image(k8sclient, self.to_nginx_image)
        # DaemonSet should have the old image version
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)

        # STEP #13
        show_step(13)
        self.delete_nginx_pods(k8sclient)

        # STEP #14
        show_step(14)
        self.wait_nginx_pods_ready(k8sclient)

        # STEP #15
        show_step(15)
        # Pods should have the old image version
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_multirollout_rollingupdate(self, underlay, k8scluster,
                                                  config, show_step):
        """Rollback multiple times a daemonset using updateStrategy type:
           RollingUpdate

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
               is updated to 1_11
               Wait for ~120 sec that the image version
               in the nginx pods is changed to 1_11
            8. Rollback the nginx daemonset:
               kubectl rollout undo daemonset/nginx
            9. Check that the image version in the nginx daemonset is
               downgraded to 1_10
               Wait for ~120 sec that the image version
               in the nginx pods is downgraded to 1_10
            10. Rollback the nginx daemonset:
               kubectl rollout undo daemonset/nginx
            11. Check that the image version in the nginx daemonset
               is updated to 1_11
               Wait for ~120 sec that the image version
               in the nginx pods is changed to 1_11
            12. Rollback the nginx daemonset:
               kubectl rollout undo daemonset/nginx
            13. Check that the image version in the nginx daemonset is
               downgraded to 1_10
               Wait for ~120 sec that the image version
               in the nginx pods is downgraded to 1_10

        Duration: 3000 seconds
        """

        self.test_daemonset_rollout_rollingupdate(underlay, k8scluster,
                                                  config, show_step)
        k8sclient = k8scluster.api

        # STEP #10
        show_step(10)
        self.rollout_daemonset(underlay, config)

        # STEP #11
        show_step(11)
        self.check_nginx_ds_image(k8sclient, self.to_nginx_image)
        # Pods should have new image version
        helpers.wait_pass(
            lambda: self.check_nginx_pods_image(
                k8sclient,
                self.to_nginx_image),
            timeout=2 * 60
        )

        # STEP #12
        show_step(12)
        self.rollout_daemonset(underlay, config)

        # STEP #13
        show_step(13)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)
        # Pods should have new image version
        helpers.wait_pass(
            lambda: self.check_nginx_pods_image(
                k8sclient,
                self.from_nginx_image),
            timeout=2 * 60
        )

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_multirollout_rollingupdate_revision(self,
                                                           config,
                                                           k8scluster,
                                                           show_step,
                                                           underlay):
        """Rollout a daemonset using updateStrategy type: RollingUpdate and
            --to-revision argument

        Scenario:
            1. Deploy k8s using fuel-ccp-installer
            2. Create a DaemonSet for nginx with image version 1_10 and
               update strategy RollingUpdate
            3. Wait until nginx pods are created and become 'ready'
            4. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            5. Change nginx image version to 1_11 using YAML
            6. Check that the image version in the nginx daemonset
               is updated to 1_11
               Wait for ~120 sec that the image version in the nginx pods
               is changed to 1_11
            7. Change nginx image version to 1_12 using YAML
            8. Check that the image version in the nginx daemonset
                is updated to 1_12.
               Wait for ~120 sec that the image version in the nginx pods
               is changed to 1_12 .
            9. Get the revision #1 and check that there are the image
               version 1_10
            10. Get the revision #2 and check that there are the image
                version 1_11
            11. Get the revision #3 and check that there are the image
                version 1_12
            12. Rollback the nginx daemonset to revision #1:
                kubectl rollout undo daemonset/nginx --to-revision=1
            13. Check that the image version in the nginx daemonset
                is updated to 1_10
                Wait for ~120 sec that the image version in the nginx pods
                is changed to 1_10
            14. Rollback the nginx daemonset:
                kubectl rollout undo daemonset/nginx
            15. Check that the image version in the nginx daemonset
                is updated to 1_12
                Wait for ~120 sec that the image version in the nginx pods
                is changed to 1_12

        Duration: 3000 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8scluster.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        nginx_spec = self.get_nginx_spec()
        self.create_daemonset(nginx_spec, k8sclient)

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
        self.update_daemonset(nginx_spec, k8sclient, self.to_nginx_image)

        # STEP #6
        show_step(6)

        # DaemonSet should have new image version
        self.check_nginx_ds_image(k8sclient, self.to_nginx_image)
        # Pods should have new image version
        helpers.wait_pass(
            lambda: self.check_nginx_pods_image(
                k8sclient,
                self.to_nginx_image),
            timeout=2 * 60)

        # STEP #7
        show_step(7)
        self.update_daemonset(nginx_spec, k8sclient, self.to_nginx_image_1_12)

        # STEP #8
        show_step(8)

        # DaemonSet should have new image version
        self.check_nginx_ds_image(k8sclient, self.to_nginx_image_1_12)
        # Pods should have new image version
        helpers.wait_pass(
            lambda: self.check_nginx_pods_image(
                k8sclient,
                self.to_nginx_image_1_12),
            timeout=2 * 60)

        # STEP #9
        show_step(9)
        self.check_nginx_revision_image(config=config.k8s.kube_host,
                                        underlay=underlay,
                                        revision="1",
                                        nginx_image=self.from_nginx_image)

        # STEP #10
        show_step(10)
        self.check_nginx_revision_image(config=config.k8s.kube_host,
                                        underlay=underlay,
                                        revision="2",
                                        nginx_image=self.to_nginx_image)

        # STEP #11
        show_step(11)
        self.check_nginx_revision_image(config=config.k8s.kube_host,
                                        underlay=underlay,
                                        revision="3",
                                        nginx_image=self.to_nginx_image_1_12)

        # STEP #12
        show_step(12)
        self.rollout_daemonset(underlay, config, revision=1)

        # STEP #13
        show_step(13)
        self.check_nginx_ds_image(k8sclient, self.to_nginx_image)
        # Pods should have old image version
        helpers.wait_pass(
            lambda: self.check_nginx_pods_image(
                k8sclient,
                self.from_nginx_image),
            timeout=2 * 60
        )

        # STEP #14
        show_step(14)
        self.rollout_daemonset(underlay, config)

        # STEP #15
        show_step(15)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)
        # Pods should have new image version
        helpers.wait_pass(
            lambda: self.check_nginx_pods_image(
                k8sclient,
                self.to_nginx_image_1_12),
            timeout=2 * 60
        )

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_multirollout_rollingupdate_default(self, underlay,
                                                          k8scluster,
                                                          config,
                                                          show_step):
        """Rollback multiple times a daemonset using updateStrategy type:
           RollingUpdate --to-revision=0

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
               is updated to 1_11
               Wait for ~120 sec that the image version
               in the nginx pods is changed to 1_11
            8. Rollback the nginx daemonset:
               kubectl rollout undo daemonset/nginx
            9. Check that the image version in the nginx daemonset is
               downgraded to 1_10
               Wait for ~120 sec that the image version
               in the nginx pods is downgraded to 1_10
            10. Rollback the nginx daemonset:
               kubectl rollout undo daemonset/nginx --to-revision=0
            11. Check that the image version in the nginx daemonset
               is updated to 1_11
               Wait for ~120 sec that the image version
               in the nginx pods is changed to 1_11
            12. Rollback the nginx daemonset:
               kubectl rollout undo daemonset/nginx --to-revision=0
            13. Check that the image version in the nginx daemonset is
               downgraded to 1_10
               Wait for ~120 sec that the image version
               in the nginx pods is downgraded to 1_10

        Duration: 3000 seconds
        """

        self.test_daemonset_rollout_rollingupdate(underlay, k8scluster,
                                                  config, show_step)
        k8sclient = k8scluster.api

        # STEP #10
        show_step(10)
        self.rollout_daemonset(underlay, config, revision=0)

        # STEP #11
        show_step(11)
        self.check_nginx_ds_image(k8sclient, self.to_nginx_image)
        # Pods should have new image version
        helpers.wait_pass(
            lambda: self.check_nginx_pods_image(
                k8sclient,
                self.to_nginx_image),
            timeout=2 * 60
        )

        # STEP #12
        show_step(12)
        self.rollout_daemonset(underlay, config, revision=1)

        # STEP #13
        show_step(13)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)
        # Pods should have new image version
        helpers.wait_pass(
            lambda: self.check_nginx_pods_image(
                k8sclient,
                self.from_nginx_image),
            timeout=2 * 60
        )

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_skip_rollout(self, underlay, k8scluster,
                                    config, show_step):
        """Testing of skipping rollout for a daemonset
        using updateStrategy type: RollingUpdate if no updates after initial
        daemonset creacting

        Scenario:
            1. Deploy k8s using fuel-ccp-installer
            2. Create a DaemonSet for nginx with image version 1_10 and
               update strategy RollingUpdate
            3. Wait until nginx pods are created and become 'ready'
            4. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            5. Rollback the nginx daemonset:
               kubectl rollout undo daemonset/nginx
            6. Check that rollout was skipped and pods were not restarted
        Duration: 3000 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8scluster.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        nginx_spec = self.get_nginx_spec()
        self.create_daemonset(nginx_spec, k8sclient)

        # STEP #3
        show_step(3)
        time.sleep(3)
        self.wait_nginx_pods_ready(k8sclient)

        # STEP #4
        show_step(4)
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)

        # STEP #5,6
        show_step(5)
        show_step(6)
        self.check_rollout_skipping(k8sclient, config.k8s.kube_host, underlay)

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_skip_rollout_revision(self, underlay, k8scluster,
                                             config, show_step):
        """Testing of skipping rollout for a daemonset
        using updateStrategy type: RollingUpdate if no updates after initial
        daemonset creacting

        Scenario:
            1. Deploy k8s using fuel-ccp-installer
            2. Create a DaemonSet for nginx with image version 1_10 and
               update strategy RollingUpdate
            3. Wait until nginx pods are created and become 'ready'
            4. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            5. Rollback the nginx daemonset:
               kubectl rollout undo daemonset/nginx --to-revision
            6. Check that rollout was skipped and pods were not restarted
        Duration: 3000 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8scluster.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        nginx_spec = self.get_nginx_spec()
        self.create_daemonset(nginx_spec, k8sclient)

        # STEP #3
        show_step(3)
        time.sleep(3)
        self.wait_nginx_pods_ready(k8sclient)

        # STEP #4
        show_step(4)
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)

        # STEP #5,6
        show_step(5)
        show_step(6)
        self.check_rollout_skipping(k8sclient, config.k8s.kube_host,
                                    underlay, revision=True)

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_rollout_revision_negative_1(self, underlay, k8scluster,
                                                   config, show_step):
        """Test handling of negative values for --to-revision argument
            for kubectl rollout undo daemonset/<name>

        Scenario:
            1. Deploy k8s using fuel-ccp-installer
            2. Create a DaemonSet for nginx with image version 1_10 and
               update strategy RollingUpdate
            3. Wait until nginx pods are created and become 'ready'
            4. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            5. Rollback the nginx daemonset:
               kubectl rollout undo daemonset/nginx --to-revision=-1
               Check that rollout was failed and pods were not restarted
        Duration: 3000 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8scluster.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        nginx_spec = self.get_nginx_spec()
        self.create_daemonset(nginx_spec, k8sclient)

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
        pods_start_time = self.get_nginx_pod_start_time(k8sclient)

        cmd = "kubectl rollout undo daemonset/nginx --to-revision=-1"
        underlay.check_call(cmd, expected=[1], host=config.k8s.kube_host)

        pods_start_time_after_cmd = self.get_nginx_pod_start_time(k8sclient)

        assert pods_start_time == pods_start_time_after_cmd, (
            "pod's restarted. pods start time before rollout: \n{}\n "
            "pods start time after rollout: \n{}".format(
                pods_start_time,
                pods_start_time_after_cmd)
        )

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_rollout_revision_negative_2(self, underlay, k8scluster,
                                                   config, show_step):
        """Test handling of negative values for --to-revision argument
            for kubectl rollout undo daemonset/<name>

        Scenario:
            1. Deploy k8s using fuel-ccp-installer
            2. Create a DaemonSet for nginx with image version 1_10 and
               update strategy RollingUpdate
            3. Wait until nginx pods are created and become 'ready'
            4. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            5. Rollback the nginx daemonset:
               kubectl rollout undo daemonset/nginx --to-revision="invalid"
               Check that rollout was failed and pods were not restarted

        Duration: 3000 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8scluster.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        nginx_spec = self.get_nginx_spec()
        self.create_daemonset(nginx_spec, k8sclient)

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
        pods_start_time = self.get_nginx_pod_start_time(k8sclient)

        cmd = "kubectl rollout undo daemonset/nginx --to-revision='invalid'"
        underlay.check_call(cmd, expected=[1], host=config.k8s.kube_host)

        pods_start_time_after_cmd = self.get_nginx_pod_start_time(k8sclient)

        assert pods_start_time == pods_start_time_after_cmd, (
            "pod's restarted. pods start time before rollout: \n{}\n "
            "pods start time after rollout: \n{}".format(
                pods_start_time,
                pods_start_time_after_cmd)
        )

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_rollout_revision_negative_3(self, underlay, k8scluster,
                                                   config, show_step):
        """Test handling of negative values for --to-revision argument
            for kubectl rollout undo daemonset/<name>

        Scenario:
            1. Deploy k8s using fuel-ccp-installer
            2. Create a DaemonSet for nginx with image version 1_10 and
               update strategy RollingUpdate
            3. Wait until nginx pods are created and become 'ready'
            4. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            5. Rollback the nginx daemonset:
               kubectl rollout undo daemonset/nginx --to-revision=1.0
               Check that rollout was failed and pods were not restarted
        Duration: 3000 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8scluster.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        nginx_spec = self.get_nginx_spec()
        self.create_daemonset(nginx_spec, k8sclient)

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
        pods_start_time = self.get_nginx_pod_start_time(k8sclient)

        cmd = "kubectl rollout undo daemonset/nginx --to-revision=1.0"
        underlay.check_call(cmd, expected=[1], host=config.k8s.kube_host)

        pods_start_time_after_cmd = self.get_nginx_pod_start_time(k8sclient)

        assert pods_start_time == pods_start_time_after_cmd, (
            "pod's restarted. pods start time before rollout: \n{}\n "
            "pods start time after rollout: \n{}".format(
                pods_start_time,
                pods_start_time_after_cmd)
        )

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_rollout_revision_negative_4(self, underlay, k8scluster,
                                                   config, show_step):
        """Test handling of negative values for --to-revision argument
            for kubectl rollout undo daemonset/<name>

        Scenario:
            1. Deploy k8s using fuel-ccp-installer
            2. Create a DaemonSet for nginx with image version 1_10 and
               update strategy RollingUpdate
            3. Wait until nginx pods are created and become 'ready'
            4. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            5. Rollback the nginx daemonset:
               kubectl rollout undo daemonset/nginx --to-revision=true
               Check that rollout was failed and pods were not restarted

        Duration: 3000 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8scluster.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        nginx_spec = self.get_nginx_spec()
        self.create_daemonset(nginx_spec, k8sclient)

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
        pods_start_time = self.get_nginx_pod_start_time(k8sclient)

        cmd = "kubectl rollout undo daemonset/nginx --to-revision=true"
        underlay.check_call(cmd, expected=[1], host=config.k8s.kube_host)

        pods_start_time_after_cmd = self.get_nginx_pod_start_time(k8sclient)

        assert pods_start_time == pods_start_time_after_cmd, (
            "pod's restarted. pods start time before rollout: \n{}\n "
            "pods start time after rollout: \n{}".format(
                pods_start_time,
                pods_start_time_after_cmd)
        )

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_scale_update_rolling_update_1(self, underlay,
                                                     k8scluster, hardware,
                                                     show_step):
        """Update a daemonset using updateStrategy type: RollingUpdate
            Scale two k8s nodes after daemonset was updated

        Scenario:
            1. Deploy k8s using fuel-ccp-installer
            2. Create a DaemonSet for nginx with image version 1_10 and
               update strategy RollingUpdate
            3. Wait until nginx pods are created and become 'ready'
            4. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            5. Change nginx image version to 1_11 using YAML
            6. Check that the image version in the nginx daemonset
               is updated to 1_11
               Wait for ~120 sec that the image version in the nginx pods
               is changed to 1_11
            7. Add to 'underlay' new nodes for k8s scale
            8. Run fuel-ccp installer for old+new k8s nodes
            9. Check number of kube nodes match underlay nodes.
            10. Check that the image version in the nginx pods is 1_11
                Check that the image version in the nginx daemonset is 1_11

        Duration: 3000 seconds
        """

        self.test_daemonset_rollingupdate(k8scluster, show_step)

        k8sclient = k8scluster.api

        # STEP #6
        show_step(7)
        config_ssh_scale = hardware.get_ssh_data(
            roles=[ext.NODE_ROLE.k8s_scale])
        underlay.add_config_ssh(config_ssh_scale)

        # STEP #8
        show_step(8)
        k8scluster.install_k8s()

        # STEP #9
        show_step(9)
        self.check_number_kube_nodes(underlay, k8sclient)

        # STEP #10
        show_step(10)
        self.check_nginx_pods_image(k8sclient, self.to_nginx_image)
        self.check_nginx_ds_image(k8sclient, self.to_nginx_image)

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_scale_update_rolling_update_2(self, underlay,
                                                     k8scluster, hardware,
                                                     show_step):
        """Update a daemonset using updateStrategy type: Noop
            Scale two k8s nodes before update daemonset

        Scenario:
            1. Deploy k8s using fuel-ccp-installer
            2. Create a DaemonSet for nginx with image version 1_10 and
               update strategy RollingUpdate
            3. Wait until nginx pods are created and become 'ready'
            4. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            5. Add to 'underlay' new nodes for k8s scale
            6. Run fuel-ccp installer for old+new k8s nodes
            7. Check number of kube nodes match underlay nodes.
            8. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            9. Change nginx image version to 1_11 using YAML
            10. Check that the image version in the nginx daemonset
               is updated to 1_11
               Wait for ~120 sec that the image version in the nginx pods
               is changed to 1_11

        Duration: 3000 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8scluster.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        nginx_spec = self.get_nginx_spec()
        self.create_daemonset(nginx_spec, k8sclient)

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
        config_ssh_scale = hardware.get_ssh_data(
            roles=[ext.NODE_ROLE.k8s_scale])
        underlay.add_config_ssh(config_ssh_scale)

        # STEP #6
        show_step(6)
        k8scluster.install_k8s()

        # STEP #7
        show_step(7)
        self.check_number_kube_nodes(underlay, k8sclient)

        # STEP #8
        show_step(8)
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)

        # STEP #9
        show_step(9)
        self.update_daemonset(nginx_spec, k8sclient, self.to_nginx_image)

        # STEP #10
        show_step(10)

        # DaemonSet should have new image version
        self.check_nginx_ds_image(k8sclient, self.to_nginx_image)
        # Pods should have new image version
        helpers.wait_pass(
            lambda: self.check_nginx_pods_image(
                k8sclient,
                self.to_nginx_image),
            timeout=2 * 60)

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_scale_rollout_rolling_update_1(self, config,
                                                      underlay, k8scluster,
                                                      hardware, show_step):
        """Rollout a daemonset using updateStrategy type: Noop
            Scale two k8s nodes after rollout daemonset

        Scenario:
            1. Deploy k8s using fuel-ccp-installer
            2. Create a DaemonSet for nginx with image version 1_10 and
               update strategy RollingUpdate
            3. Wait until nginx pods are created and become 'ready'
            4. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            5. Change nginx image version to 1_11 using YAML
            6. Check that the image version in the nginx daemonset
               is updated to 1_11
               Wait for ~120 sec that the image version in the nginx pods
               is changed to 1_11
            7. Rollback the nginx daemonset:
               kubectl rollout undo daemonset/nginx
            8. Check that the image version in the nginx daemonset is
               downgraded to 1_10
               Wait for ~120 sec that the image version
               in the nginx pods is downgraded to 1_10
            9. Add to 'underlay' new nodes for k8s scale
            10. Run fuel-ccp installer for old+new k8s nodes
            11. Check number of kube nodes match underlay nodes.
            12. Check that the image version in the nginx pods is 1_10
                Check that the image version in the nginx daemonset is 1_10

        Duration: 3000 seconds
        """
        self.test_daemonset_rollout_rollingupdate(underlay, k8scluster,
                                                  config, show_step)
        k8sclient = k8scluster.api

        # STEP #9
        show_step(9)
        config_ssh_scale = hardware.get_ssh_data(
            roles=[ext.NODE_ROLE.k8s_scale])
        underlay.add_config_ssh(config_ssh_scale)

        # STEP #10
        show_step(10)
        k8scluster.install_k8s()

        # STEP #11
        show_step(11)
        self.check_number_kube_nodes(underlay, k8sclient)

        # STEP #12
        show_step(12)
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_scale_rollout_rolling_update2(self, underlay,
                                                     config, k8scluster,
                                                     hardware, show_step):
        """Rollout a daemonset using updateStrategy type: Rollingupdate
            Scale two k8s nodes before rollout daemonset

        Scenario:
            1. Deploy k8s using fuel-ccp-installer
            2. Create a DaemonSet for nginx with image version 1_10 and
               update strategy RollingUpdate
            3. Wait until nginx pods are created and become 'ready'
            4. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            5. Add to 'underlay' new nodes for k8s scale
            6. Run fuel-ccp installer for old+new k8s nodes
            7. Check number of kube nodes match underlay nodes.
            8. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            9. Change nginx image version to 1_11 using YAML
            10. Check that the image version in the nginx daemonset
               is updated to 1_11
               Wait for ~120 sec that the image version in the nginx pods
               is changed to 1_11
            11. Rollback the nginx daemonset:
               kubectl rollout undo daemonset/nginx
            12. Check that the image version in the nginx daemonset is
               downgraded to 1_10
               Wait for ~120 sec that the image version
               in the nginx pods is downgraded to 1_10

        Duration: 3000 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8scluster.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        nginx_spec = self.get_nginx_spec()
        self.create_daemonset(nginx_spec, k8sclient)

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
        config_ssh_scale = hardware.get_ssh_data(
            roles=[ext.NODE_ROLE.k8s_scale])
        underlay.add_config_ssh(config_ssh_scale)

        # STEP #6
        show_step(6)
        k8scluster.install_k8s()

        # STEP #7
        show_step(7)
        self.check_number_kube_nodes(underlay, k8sclient)

        # STEP #8
        show_step(8)
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)

        # STEP #9
        show_step(9)
        self.update_daemonset(nginx_spec, k8sclient, self.to_nginx_image)

        # STEP #10
        show_step(10)

        # DaemonSet should have new image version
        self.check_nginx_ds_image(k8sclient, self.to_nginx_image)
        # Pods should have new image version
        helpers.wait_pass(
            lambda: self.check_nginx_pods_image(
                k8sclient,
                self.to_nginx_image),
            timeout=2 * 60)

        # STEP #11
        show_step(11)
        self.rollout_daemonset(underlay, config)

        # STEP #12
        show_step(12)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)
        # Pods should have new image version
        helpers.wait_pass(
            lambda: self.check_nginx_pods_image(
                k8sclient,
                self.from_nginx_image),
            timeout=2 * 60
        )

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_scale_noop_update_1(self, hardware, underlay,
                                           k8scluster, show_step):
        """Update a daemonset using updateStrategy type: Noop
            Scale two k8s nodes after daemonset updated

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
           11. Add to 'underlay' new nodes for k8s scale
           12. Run fuel-ccp installer for old+new k8s nodes
           13. Check number of kube nodes match underlay nodes.
           14. Check that the image version in the nginx pods is 1_11
                Check that the image version in the nginx daemonset is 1_11


        Duration: 3000 seconds
        """
        self.test_daemonset_rollingupdate_noop(k8scluster, show_step)

        k8sclient = k8scluster.api

        # STEP #11
        show_step(11)
        config_ssh_scale = hardware.get_ssh_data(
            roles=[ext.NODE_ROLE.k8s_scale])
        underlay.add_config_ssh(config_ssh_scale)

        # STEP #12
        show_step(12)
        k8scluster.install_k8s()

        # STEP #13
        show_step(13)
        self.check_number_kube_nodes(underlay, k8sclient)

        # STEP #14
        show_step(14)
        self.check_nginx_pods_image(k8sclient, self.to_nginx_image)
        self.check_nginx_ds_image(k8sclient, self.to_nginx_image)

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_scale_noop_update_2(self, hardware, underlay,
                                           k8scluster, show_step):
        """Update a daemonset using updateStrategy type: Noop
           Scale two k8s nodes before update daemonset

        Scenario:
            1. Deploy k8s using fuel-ccp-installer
            2. Create a DaemonSet for nginx with image version 1_10 and
               update strategy Noop
            3. Wait until nginx pods are created and become 'ready'
            4. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            5. Add to 'underlay' new nodes for k8s scale
            6. Run fuel-ccp installer for old+new k8s nodes
            7. Check number of kube nodes match underlay nodes.
            8. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            9. Change nginx image version to 1_11 using YAML
            10. Wait for 10 seconds (needs to check that there were
               no auto updates of the nginx pods)
            11. Check that the image version in the nginx pods is still 1_10
               Check that the image version in the nginx daemonset
               is updated to 1_11
            12. Kill all nginx pods that are belong to the nginx daemonset
            13. Wait until nginx pods are created and become 'ready'
            14. Check that the image version in the nginx pods
               is updated to 1_11
            15. Check that the image version in the nginx pods is 1_11
                Check that the image version in the nginx daemonset is 1_11


        Duration: 3000 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8scluster.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        nginx_spec = self.get_nginx_spec()
        self.create_daemonset(nginx_spec, k8sclient, noop=True)

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
        config_ssh_scale = hardware.get_ssh_data(
            roles=[ext.NODE_ROLE.k8s_scale])
        underlay.add_config_ssh(config_ssh_scale)

        # STEP #6
        show_step(6)
        k8scluster.install_k8s()

        # STEP #7
        show_step(7)
        self.check_number_kube_nodes(underlay, k8sclient)

        # STEP #8
        show_step(8)
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)

        # STEP #9
        show_step(9)
        self.update_daemonset(nginx_spec, k8sclient, self.to_nginx_image)

        # STEP #10
        show_step(10)
        time.sleep(10)

        # STEP #11
        show_step(11)
        # Pods should still have the old image version
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)
        # DaemonSet should have new image version
        self.check_nginx_ds_image(k8sclient, self.to_nginx_image)

        # STEP #12
        show_step(12)
        self.delete_nginx_pods(k8sclient)

        # STEP #13
        show_step(13)
        self.wait_nginx_pods_ready(k8sclient)

        # STEP #14
        show_step(14)
        # Pods should have the new image version
        self.check_nginx_pods_image(k8sclient, self.to_nginx_image)

        # STEP #15
        show_step(15)
        self.check_nginx_pods_image(k8sclient, self.to_nginx_image)
        self.check_nginx_ds_image(k8sclient, self.to_nginx_image)

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_scale_noop_rollout_1(self, underlay, k8scluster,
                                            config, hardware, show_step):
        """Rollback a daemonset using updateStrategy type: Noop

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
           11. Rollout the daemonset to a previous revision:
                kubectl rollout undo daemonset/nginx
           12. Check that the image version in the nginx pods is still 1_11
               Check that the image version in the nginx daemonset
               is changed to 1_10
           13. Kill all nginx pods that are belong to the nginx daemonset
           14. Wait until nginx pods are created and become 'ready'
           15. Check that the image version in the nginx pods
               is changed to 1_10
           16. Add to 'underlay' new nodes for k8s scale
           17. Run fuel-ccp installer for old+new k8s nodes
           18. Check number of kube nodes match underlay nodes.
           19. Check that the image version in the nginx pods is 1_10
                Check that the image version in the nginx daemonset is 1_10



        Duration: 3000 seconds
        """

        self.test_daemonset_rollout_noop(underlay, k8scluster,
                                         config, show_step)

        k8sclient = k8scluster.api

        # STEP #16
        show_step(16)
        config_ssh_scale = hardware.get_ssh_data(
            roles=[ext.NODE_ROLE.k8s_scale])
        underlay.add_config_ssh(config_ssh_scale)

        # STEP #17
        show_step(17)
        k8scluster.install_k8s()

        # STEP #18
        show_step(18)
        self.check_number_kube_nodes(underlay, k8sclient)

        # STEP #19
        show_step(19)
        self.check_nginx_pods_image(k8sclient, self.to_nginx_image)
        self.check_nginx_ds_image(k8sclient, self.to_nginx_image)

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_scale_noop_rollout_2(self, underlay,
                                            k8scluster, config, hardware,
                                            show_step):
        """Rollback a daemonset using updateStrategy type: Noop

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
           11. Add to 'underlay' new nodes for k8s scale
           12. Run fuel-ccp installer for old+new k8s nodes
           13. Check number of kube nodes match underlay nodes.
           14. Check that the image version in the nginx pods is 1_11
                Check that the image version in the nginx daemonset is 1_11
           15. Rollout the daemonset to a previous revision:
                kubectl rollout undo daemonset/nginx
           16. Check that the image version in the nginx pods is still 1_11
               Check that the image version in the nginx daemonset
               is changed to 1_10
           17. Kill all nginx pods that are belong to the nginx daemonset
           18. Wait until nginx pods are created and become 'ready'
           19. Check that the image version in the nginx pods
               is changed to 1_10



        Duration: 3000 seconds
        """

        self.test_daemonset_rollingupdate_noop(k8scluster, show_step)

        k8sclient = k8scluster.api

        # STEP #11
        show_step(11)
        config_ssh_scale = hardware.get_ssh_data(
            roles=[ext.NODE_ROLE.k8s_scale])
        underlay.add_config_ssh(config_ssh_scale)

        # STEP #12
        show_step(12)
        k8scluster.install_k8s()

        # STEP #13
        show_step(13)
        self.check_number_kube_nodes(underlay, k8sclient)

        # STEP #14
        show_step(14)
        self.check_nginx_pods_image(k8sclient, self.to_nginx_image)
        self.check_nginx_ds_image(k8sclient, self.to_nginx_image)

        # STEP #15
        show_step(15)
        self.rollout_daemonset(underlay, config, revision=1)

        # STEP #16
        show_step(16)
        # Pods should still have the new image version
        self.check_nginx_pods_image(k8sclient, self.to_nginx_image)
        # DaemonSet should have the old image version
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)

        # STEP #17
        show_step(17)
        self.delete_nginx_pods(k8sclient)

        # STEP #18
        show_step(18)
        self.wait_nginx_pods_ready(k8sclient)

        # STEP #19
        show_step(19)
        # Pods should have the old image version
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)
