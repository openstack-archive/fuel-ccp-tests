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
import yaml

from devops.helpers import helpers
import pytest

from fuel_ccp_tests import logger

LOG = logger.logger


class TestDaemonsetsUpdates():
    """Test class for update DaemonSets"""

    from_nginx_image = 'nginx:1.10'
    to_nginx_image = 'nginx:1.11'
    to_nginx_image_1_12 = 'nginx:1.12'
    nginx_spec_path = '/tmp/nginx-ds.yaml'

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
                'annotations': {
                    'daemonset.kubernetes.io/strategyType': 'RollingUpdate',
                    'daemonset.kubernetes.io/maxUnavailable': '1'},
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
                }
            }
        }

    def write_spec_to_yaml(self, spec, path, underlay, config):
        with underlay.remote(host=config.k8s.kube_host) as r:
            with r.open(path, "w") as f:
                f.write(yaml.safe_dump(spec, default_flow_style=False))

    def get_ds_upgrade_controller_spec(self):
        """Create specification for Daemonset Upgrade controller
                    :return: nested dict
                """
        return {
            'apiVersion': 'extensions/v1beta1',
            'kind': 'Deployment',
            'metadata': {
                'name': 'daemonupgrader',
            },
            'spec': {
                'replicas': 1,
                'template': {
                    'metadata': {
                        'labels': {'app': 'daemonupgrader'}},
                    'spec': {
                        'containers': [
                            {'name': 'daemonupgrader',
                             'image': 'mirantis/'
                                      'k8s-daemonupgradecontroller:latest',
                             'imagePullPolicy': 'IfNotPresent'},
                        ],
                    },
                }
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
                "Pod {0} has image {1} "
                "while expected {2}".format(pod.name, pod_image, nginx_image))

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
                "DaemonSet {0} has image {1} "
                "while expected {2}".format(nginx_ds.name, nginx_ds_image,
                                            nginx_image))

    def check_nginx_revision_image(self, config, underlay,
                                   revision, nginx_image):

        cmd = 'kubectl get podtemplate -l \"app=nginx\" -o yaml'

        nginx_revision_images = underlay.check_call(cmd,
                                                    host=config
                                                    )['stdout_yaml']
        temp = {}
        for rev in range(len(nginx_revision_images['items'])):
            temp[nginx_revision_images['items'][rev]['metadata'][
                'annotations'].values()[0]] = \
                nginx_revision_images['items'][rev]['template']['spec'][
                    'containers'][0]['image']
        assert temp[revision] == nginx_image, (
            "revision {0} has image {1} while expected {2}".format(
                revision, temp[revision], nginx_image))

    def get_nginx_pod_start_time(self, k8sclient):
        start_time = {}
        for pod in self.get_nginx_pods(k8sclient):
            start_time[pod.name] = pod.status._container_statuses[
                0].state.running.started_at
        return start_time

    def check_rollout_skipping(self, k8sclient, nginx_spec_path,
                               config, underlay, revision=None):

        # collect pods start time
        start_time = self.get_nginx_pod_start_time(k8sclient)
        with underlay.yaml_editor(nginx_spec_path,
                                  host=config) as editor:

            # try to rollout
            if revision:
                editor.content['metadata']['annotations'][
                    'daemonset.kubernetes.io/rollbackTo'] = revision
            else:
                editor.content['metadata']['annotations'][
                    'daemonset.kubernetes.io/rollbackTo'] = "0"

        cmd = "kubectl apply -f {}".format(nginx_spec_path)
        underlay.check_call(cmd, host=config)
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)

        # check that pods start time don't changed
        # collect pods start time
        start_time_after_rollout = self.get_nginx_pod_start_time(k8sclient)

        assert start_time == start_time_after_rollout, (
            "pod's restarted. pods start time before rollout: \n{}\n "
            "pods start time after rollout: \n{}".format(
                start_time,
                start_time_after_rollout)
        )

    def rollout_undo_daemonset(self, underlay, config,
                               nginx_spec_path, to_revision=None):
        """Rollout nginx Daemonset
        """
        with underlay.yaml_editor(nginx_spec_path,
                                  host=config.k8s.kube_host) as editor:
            if to_revision:
                editor.content['metadata']['annotations'][
                    'daemonset.kubernetes.io/rollbackTo'] = to_revision
            else:
                editor.content['metadata']['annotations'][
                    'daemonset.kubernetes.io/rollbackTo'] = "0"

        cmd = "kubectl apply -f {}".format(nginx_spec_path)
        underlay.check_call(cmd, host=config.k8s.kube_host)

    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_rollingupdate_noop(self, config, k8scluster,
                                          show_step, underlay):
        """Update a daemonset using updateStrategy type: Noop

        Scenario:
            1. Deploy k8s using fuel-ccp-installer
            2. Create a Deployment for Daemonset Upgrade controller
            3. Create a DaemonSet for nginx with image version 1_10 and
               update strategy Noop
            4. Wait until nginx pods are created and become 'ready'
            5. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            6. Change nginx image version to 1_11 using YAML
            7. Wait for 30 seconds (needs to check that there were
               no auto updates of the nginx pods)
            8. Check that the image version in the nginx pods is still 1_10
               Check that the image version in the nginx daemonset
               is updated to 1_11
            9. Kill all nginx pods that are belong to the nginx daemonset
           10. Wait until nginx pods are created and become 'ready'
           11. Check that the image version in the nginx pods
               is updated to 1_11

        Duration: 3000 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8scluster.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        ds_controller_spec = self.get_ds_upgrade_controller_spec()
        k8sclient.deployments.create(body=ds_controller_spec)

        # STEP #3
        show_step(3)
        nginx_spec = self.get_nginx_spec()
        self.write_spec_to_yaml(nginx_spec, self.nginx_spec_path, underlay,
                                config)
        with underlay.yaml_editor(self.nginx_spec_path,
                                  host=config.k8s.kube_host) as editor:
            editor.content['metadata']['annotations'][
                'daemonset.kubernetes.io/strategyType'] = 'Noop'
            editor.content['spec']['template']['spec']['containers'][0][
                'image'] = self.from_nginx_image

        cmd = "kubectl create -f {}".format(self.nginx_spec_path)
        underlay.check_call(cmd, host=config.k8s.kube_host)

        # STEP #4
        show_step(4)
        time.sleep(4)
        self.wait_nginx_pods_ready(k8sclient)

        # STEP #5
        show_step(5)
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)

        # STEP #6
        show_step(6)
        with underlay.yaml_editor(self.nginx_spec_path,
                                  host=config.k8s.kube_host) as editor:
            editor.content['spec']['template']['spec']['containers'][0][
                'image'] = self.to_nginx_image
        cmd = "kubectl apply -f {}".format(self.nginx_spec_path)
        underlay.check_call(cmd, host=config.k8s.kube_host)

        # STEP #7
        show_step(7)
        time.sleep(30)

        # STEP #8
        show_step(8)
        # Pods should still have the old image version
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)
        # DaemonSet should have new image version
        self.check_nginx_ds_image(k8sclient, self.to_nginx_image)

        # STEP #9
        show_step(9)
        self.delete_nginx_pods(k8sclient)

        # STEP #10
        show_step(10)
        self.wait_nginx_pods_ready(k8sclient)

        # STEP #11
        show_step(11)
        # Pods should have the new image version
        self.check_nginx_pods_image(k8sclient, self.to_nginx_image)

    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_rollingupdate(self, config, k8scluster,
                                     show_step, underlay):
        """Update a daemonset using updateStrategy type: RollingUpdate

        Scenario:
            1. Deploy k8s using fuel-ccp-installer
            2. Create a Deployment for Daemonset Upgrade controller
            3. Create a DaemonSet for nginx with image version 1_10 and
               update strategy RollingUpdate
            4. Wait until nginx pods are created and become 'ready'
            5. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            6. Change nginx image version to 1_11 using YAML
            7. Wait for 30 seconds (needs to check that there were
               no auto updates of the nginx pods)
            8. Check that the image version in the nginx daemonset
               is updated to 1_11
               Wait for ~180 sec that the image version in the nginx pods
               is changed to 1_11

        Duration: 3000 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8scluster.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        ds_controller_spec = self.get_ds_upgrade_controller_spec()
        k8sclient.deployments.create(body=ds_controller_spec)

        # STEP #3
        show_step(3)
        nginx_spec = self.get_nginx_spec()
        self.write_spec_to_yaml(nginx_spec, self.nginx_spec_path, underlay,
                                config)
        with underlay.yaml_editor(self.nginx_spec_path,
                                  host=config.k8s.kube_host) as editor:
            editor.content['spec']['template']['spec']['containers'][0][
                'image'] = self.from_nginx_image

        cmd = "kubectl create -f {}".format(self.nginx_spec_path)
        underlay.check_call(cmd, host=config.k8s.kube_host)

        # STEP #4
        show_step(4)
        time.sleep(30)
        self.wait_nginx_pods_ready(k8sclient)

        # STEP #5
        show_step(5)
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)

        # STEP #6
        show_step(6)
        with underlay.yaml_editor(self.nginx_spec_path,
                                  host=config.k8s.kube_host) as editor:
            editor.content['spec']['template']['spec']['containers'][0][
                'image'] = self.to_nginx_image
        cmd = "kubectl apply -f {}".format(self.nginx_spec_path)
        underlay.check_call(cmd, host=config.k8s.kube_host)

        # STEP #7
        show_step(7)
        time.sleep(30)

        # STEP #8
        show_step(8)
        # DaemonSet should have new image version
        self.check_nginx_ds_image(k8sclient, self.to_nginx_image)
        # Pods should have new image version
        helpers.wait_pass(
            lambda: self.check_nginx_pods_image(
                k8sclient,
                self.to_nginx_image),
            timeout=3 * 60)

    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_rollout_rollingupdate(self, config, k8scluster,
                                             show_step, underlay):
        """Rollback a daemonset using updateStrategy type: RollingUpdate

        Scenario:
            1. Deploy k8s using fuel-ccp-installer
            2. Create a Deployment for Daemonset Upgrade controller
            3. Create a DaemonSet for nginx with image version 1_10 and
               update strategy RollingUpdate
            4. Wait until nginx pods are created and become 'ready'
            5. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            6. Change nginx image version to 1_11 using YAML
            7. Wait for 30 seconds (needs to check that there were
               no auto updates of the nginx pods)
            8. Check that the image version in the nginx daemonset
               is updated to 1_11
               Wait for ~180 sec that the image version
               in the nginx pods is changed to 1_11
            9. Rollback the nginx daemonset
            10. Check that the image version in the nginx daemonset is
               downgraded to 1_10
               Wait for ~180 sec that the image version
               in the nginx pods is downgraded to 1_10

        Duration: 3000 seconds
        """

        self.test_daemonset_rollingupdate(config, k8scluster,
                                          show_step, underlay)

        k8sclient = k8scluster.api

        show_step(9)

        self.rollout_undo_daemonset(underlay, config, self.nginx_spec_path)

        # STEP #9
        show_step(10)
        time.sleep(30)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)
        # Pods should have new image version
        helpers.wait_pass(
            lambda: self.check_nginx_pods_image(
                k8sclient,
                self.from_nginx_image),
            timeout=3 * 60
        )

    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_rollout_noop(self, underlay,
                                    k8scluster, config, show_step):
        """Rollback a daemonset using updateStrategy type: Noop

        Scenario:
            1. Deploy k8s using fuel-ccp-installer
            2. Create a Deployment for Daemonset Upgrade controller
            3. Create a DaemonSet for nginx with image version 1_10 and
               update strategy Noop
            4. Wait until nginx pods are created and become 'ready'
            5. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            6. Change nginx image version to 1_11 using YAML
            7. Wait for 30 seconds (needs to check that there were
               no auto updates of the nginx pods)
            8. Check that the image version in the nginx pods is still 1_10
               Check that the image version in the nginx daemonset
               is updated to 1_11
            9. Kill all nginx pods that are belong to the nginx daemonset
           10 . Wait until nginx pods are created and become 'ready'
           11. Check that the image version in the nginx pods
               is updated to 1_11
           12. Rollout the daemonset to a previous revision
           13. Check that the image version in the nginx pods is still 1_11
               Check that the image version in the nginx daemonset
               is changed to 1_10
           14. Kill all nginx pods that are belong to the nginx daemonset
           15. Wait until nginx pods are created and become 'ready'
           16. Check that the image version in the nginx pods
               is changed to 1_10


        Duration: 3000 seconds
        """

        self.test_daemonset_rollingupdate_noop(config, k8scluster,
                                               show_step, underlay)

        k8sclient = k8scluster.api

        # STEP #12
        show_step(12)
        self.rollout_undo_daemonset(underlay, config, self.nginx_spec_path)

        # STEP #13
        show_step(13)
        # Pods should still have the newest image version
        self.check_nginx_pods_image(k8sclient, self.to_nginx_image)
        # DaemonSet should have the oldest image version
        time.sleep(30)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)

        # STEP #14
        show_step(14)
        self.delete_nginx_pods(k8sclient)

        # STEP #15
        show_step(15)
        self.wait_nginx_pods_ready(k8sclient)

        # STEP #16
        show_step(16)
        # Pods should have the old image version
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)

    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_multirollout_rollingupdate(self, underlay, k8scluster,
                                                  config, show_step):
        """Rollback multiple times a daemonset using updateStrategy type:
           RollingUpdate

        Scenario:
            1. Deploy k8s using fuel-ccp-installer
            2. Create a Deployment for Daemonset Upgrade controller
            3. Create a DaemonSet for nginx with image version 1_10 and
               update strategy RollingUpdate
            4. Wait until nginx pods are created and become 'ready'
            5. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            6. Change nginx image version to 1_11 using YAML
            7. Wait for 10 seconds (needs to check that there were
               no auto updates of the nginx pods)
            8. Check that the image version in the nginx daemonset
               is updated to 1_11
               Wait for ~120 sec that the image version
               in the nginx pods is changed to 1_11
            9. Rollback the nginx daemonset
            10. Check that the image version in the nginx daemonset is
               downgraded to 1_10
               Wait for ~120 sec that the image version
               in the nginx pods is downgraded to 1_10
            11. Rollback the nginx daemonset
            12. Check that the image version in the nginx daemonset
               is updated to 1_11
               Wait for ~120 sec that the image version
               in the nginx pods is changed to 1_11
            13. Rollback the nginx daemonset:
            14. Check that the image version in the nginx daemonset is
               downgraded to 1_10
               Wait for ~120 sec that the image version
               in the nginx pods is downgraded to 1_10

        Duration: 3000 seconds
        """

        self.test_daemonset_rollout_rollingupdate(config, k8scluster,
                                                  show_step, underlay)
        k8sclient = k8scluster.api

        # STEP #11
        show_step(11)
        self.rollout_undo_daemonset(underlay, config, self.nginx_spec_path)

        # STEP #12
        show_step(12)
        time.sleep(30)
        self.check_nginx_ds_image(k8sclient, self.to_nginx_image)
        # Pods should have new image version
        helpers.wait_pass(
            lambda: self.check_nginx_pods_image(
                k8sclient,
                self.to_nginx_image),
            timeout=3 * 60
        )

        # STEP #13
        show_step(13)
        self.rollout_undo_daemonset(underlay, config, self.nginx_spec_path)

        # STEP #14
        show_step(14)
        time.sleep(30)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)
        # Pods should have new image version
        helpers.wait_pass(
            lambda: self.check_nginx_pods_image(
                k8sclient,
                self.from_nginx_image),
            timeout=3 * 60
        )

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
            2. Create a Deployment for Daemonset Upgrade controller
            3. Create a DaemonSet for nginx with image version 1_10 and
               update strategy RollingUpdate
            4. Wait until nginx pods are created and become 'ready'
            5. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            6. Change nginx image version to 1_11 using YAML
            7. Check that the image version in the nginx daemonset
               is updated to 1_11
               Wait for ~120 sec that the image version in the nginx pods
               is changed to 1_11
            8. Change nginx image version to 1_12 using YAML
            9. Check that the image version in the nginx daemonset
                is updated to 1_12.
               Wait for ~120 sec that the image version in the nginx pods
               is changed to 1_12 .
            10. Get the revision #1 and check that there are the image
               version 1_10
            11. Get the revision #2 and check that there are the image
                version 1_11
            12. Get the revision #3 and check that there are the image
                version 1_12
            13. Rollback the nginx daemonset to revision #1:
                kubectl rollout undo daemonset/nginx --to-revision=1
            14. Check that the image version in the nginx daemonset
                is updated to 1_10
                Wait for ~120 sec that the image version in the nginx pods
                is changed to 1_10
            15. Rollback the nginx daemonset:
                kubectl rollout undo daemonset/nginx
            16. Check that the image version in the nginx daemonset
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
        ds_controller_spec = self.get_ds_upgrade_controller_spec()
        k8sclient.deployments.create(body=ds_controller_spec)

        # STEP #3
        show_step(3)
        nginx_spec = self.get_nginx_spec()
        self.write_spec_to_yaml(nginx_spec, self.nginx_spec_path, underlay,
                                config)
        with underlay.yaml_editor(self.nginx_spec_path,
                                  host=config.k8s.kube_host) as editor:
            editor.content['spec']['template']['spec']['containers'][0][
                'image'] = self.from_nginx_image

        cmd = "kubectl create -f {}".format(self.nginx_spec_path)
        underlay.check_call(cmd, host=config.k8s.kube_host)

        # STEP #4
        show_step(4)
        time.sleep(3)
        self.wait_nginx_pods_ready(k8sclient)

        # STEP #5
        show_step(5)
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)

        # STEP #6
        show_step(6)
        with underlay.yaml_editor(self.nginx_spec_path,
                                  host=config.k8s.kube_host) as editor:
            editor.content['spec']['template']['spec']['containers'][0][
                'image'] = self.to_nginx_image
        cmd = "kubectl apply -f {}".format(self.nginx_spec_path)
        underlay.check_call(cmd, host=config.k8s.kube_host)

        # STEP #7
        show_step(7)

        # DaemonSet should have new image version
        self.check_nginx_ds_image(k8sclient, self.to_nginx_image)
        # Pods should have new image version
        helpers.wait_pass(
            lambda: self.check_nginx_pods_image(
                k8sclient,
                self.to_nginx_image),
            timeout=3 * 60)

        # STEP #8
        show_step(8)
        with underlay.yaml_editor(self.nginx_spec_path,
                                  host=config.k8s.kube_host) as editor:
            editor.content['spec']['template']['spec']['containers'][0][
                'image'] = self.to_nginx_image_1_12
        cmd = "kubectl apply -f {}".format(self.nginx_spec_path)
        underlay.check_call(cmd, host=config.k8s.kube_host)

        # STEP #9
        show_step(9)

        # DaemonSet should have new image version
        self.check_nginx_ds_image(k8sclient, self.to_nginx_image_1_12)
        # Pods should have new image version
        helpers.wait_pass(
            lambda: self.check_nginx_pods_image(
                k8sclient,
                self.to_nginx_image_1_12),
            timeout=3 * 60)

        # STEP #10
        show_step(10)
        self.check_nginx_revision_image(config=config.k8s.kube_host,
                                        underlay=underlay,
                                        revision="1",
                                        nginx_image=self.from_nginx_image)

        # STEP #11
        show_step(11)
        self.check_nginx_revision_image(config=config.k8s.kube_host,
                                        underlay=underlay,
                                        revision="2",
                                        nginx_image=self.to_nginx_image)

        # STEP #12
        show_step(12)
        self.check_nginx_revision_image(config=config.k8s.kube_host,
                                        underlay=underlay,
                                        revision="3",
                                        nginx_image=self.to_nginx_image_1_12)

        # STEP #13
        show_step(13)
        self.rollout_undo_daemonset(underlay, config,
                                    self.nginx_spec_path, "1")

        # STEP #14
        show_step(14)
        time.sleep(30)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)
        # Pods should have old image version
        helpers.wait_pass(
            lambda: self.check_nginx_pods_image(
                k8sclient,
                self.from_nginx_image),
            timeout=3 * 60
        )

        # STEP #15
        show_step(15)
        self.rollout_undo_daemonset(underlay, config, self.nginx_spec_path)

        # STEP #16
        show_step(16)
        self.check_nginx_ds_image(k8sclient, self.to_nginx_image_1_12)
        # Pods should have new image version
        helpers.wait_pass(
            lambda: self.check_nginx_pods_image(
                k8sclient,
                self.to_nginx_image_1_12),
            timeout=2 * 60
        )

    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_skip_rollout(self, underlay, k8scluster,
                                    config, show_step):
        """Testing of skipping rollout for a daemonset
        using updateStrategy type: RollingUpdate if no updates after initial
        daemonset creacting

        Scenario:
            1. Deploy k8s using fuel-ccp-installer
            2. Create a Deployment for Daemonset Upgrade controller
            3. Create a DaemonSet for nginx with image version 1_10 and
               update strategy RollingUpdate
            4. Wait until nginx pods are created and become 'ready'
            5. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            6. Rollback the nginx daemonset
            7. Check that rollout was skipped and pods were not restarted
        Duration: 3000 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8scluster.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        ds_controller_spec = self.get_ds_upgrade_controller_spec()
        k8sclient.deployments.create(body=ds_controller_spec)

        # STEP #3
        show_step(3)
        nginx_spec = self.get_nginx_spec()
        self.write_spec_to_yaml(nginx_spec, self.nginx_spec_path, underlay,
                                config)
        with underlay.yaml_editor(self.nginx_spec_path,
                                  host=config.k8s.kube_host) as editor:
            editor.content['spec']['template']['spec']['containers'][0][
                'image'] = self.from_nginx_image

        cmd = "kubectl create -f {}".format(self.nginx_spec_path)
        underlay.check_call(cmd, host=config.k8s.kube_host)

        # STEP #4
        show_step(4)
        time.sleep(3)
        self.wait_nginx_pods_ready(k8sclient)

        # STEP #5
        show_step(5)
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)

        # STEP #6,7
        show_step(6)
        show_step(7)
        self.check_rollout_skipping(k8sclient, self.nginx_spec_path,
                                    config.k8s.kube_host, underlay)

    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_rollout_revision_negative_1(self, underlay, k8scluster,
                                                   config, show_step):
        """Test handling of negative values for --to-revision argument
            for kubectl rollout undo daemonset/<name>

        Scenario:
             1. Deploy k8s using fuel-ccp-installer
            2. Create a Deployment for Daemonset Upgrade controller
            3. Create a DaemonSet for nginx with image version 1_10 and
               update strategy RollingUpdate
            4. Wait until nginx pods are created and become 'ready'
            5. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            6. Rollback the nginx daemonset with negative revision
            7. Check that rollout was skipped and pods were not restarted
        Duration: 3000 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8scluster.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        ds_controller_spec = self.get_ds_upgrade_controller_spec()
        k8sclient.deployments.create(body=ds_controller_spec)

        # STEP #3
        show_step(3)
        nginx_spec = self.get_nginx_spec()
        self.write_spec_to_yaml(nginx_spec, self.nginx_spec_path, underlay,
                                config)
        with underlay.yaml_editor(self.nginx_spec_path,
                                  host=config.k8s.kube_host) as editor:
            editor.content['spec']['template']['spec']['containers'][0][
                'image'] = self.from_nginx_image

        cmd = "kubectl create -f {}".format(self.nginx_spec_path)
        underlay.check_call(cmd, host=config.k8s.kube_host)

        # STEP #4
        show_step(4)
        time.sleep(3)
        self.wait_nginx_pods_ready(k8sclient)

        # STEP #5
        show_step(5)
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)

        # STEP #6,7
        show_step(6)
        show_step(7)
        pods_start_time = self.get_nginx_pod_start_time(k8sclient)

        with underlay.yaml_editor(self.nginx_spec_path,
                                  host=config.k8s.kube_host) as editor:
            editor.content['metadata']['annotations'][
                'daemonset.kubernetes.io/rollbackTo'] = "-1"

        cmd = "kubectl apply -f {}".format(self.nginx_spec_path)
        underlay.check_call(cmd, host=config.k8s.kube_host)

        pods_start_time_after_cmd = self.get_nginx_pod_start_time(k8sclient)

        time.sleep(30)
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)

        assert pods_start_time == pods_start_time_after_cmd, (
            "pod's restarted. pods start time before rollout: \n{}\n "
            "pods start time after rollout: \n{}".format(
                pods_start_time,
                pods_start_time_after_cmd)
        )

    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_rollout_revision_negative_2(self, underlay, k8scluster,
                                                   config, show_step):
        """Test handling of negative values for --to-revision argument
            for kubectl rollout undo daemonset/<name>

        Scenario:
             1. Deploy k8s using fuel-ccp-installer
            2. Create a Deployment for Daemonset Upgrade controller
            3. Create a DaemonSet for nginx with image version 1_10 and
               update strategy RollingUpdate
            4. Wait until nginx pods are created and become 'ready'
            5. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            6. Rollback the nginx daemonset with chars insted digit revision
            7. Check that rollout was skipped and pods were not restarted
        Duration: 3000 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8scluster.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        ds_controller_spec = self.get_ds_upgrade_controller_spec()
        k8sclient.deployments.create(body=ds_controller_spec)

        # STEP #3
        show_step(3)
        nginx_spec = self.get_nginx_spec()
        self.write_spec_to_yaml(nginx_spec, self.nginx_spec_path, underlay,
                                config)
        with underlay.yaml_editor(self.nginx_spec_path,
                                  host=config.k8s.kube_host) as editor:
            editor.content['spec']['template']['spec']['containers'][0][
                'image'] = self.from_nginx_image

        cmd = "kubectl create -f {}".format(self.nginx_spec_path)
        underlay.check_call(cmd, host=config.k8s.kube_host)

        # STEP #4
        show_step(4)
        time.sleep(3)
        self.wait_nginx_pods_ready(k8sclient)

        # STEP #5
        show_step(5)
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)

        # STEP #6,7
        show_step(6)
        show_step(7)
        pods_start_time = self.get_nginx_pod_start_time(k8sclient)

        with underlay.yaml_editor(self.nginx_spec_path,
                                  host=config.k8s.kube_host) as editor:
            editor.content['metadata']['annotations'][
                'daemonset.kubernetes.io/rollbackTo'] = "invalid"

        cmd = "kubectl apply -f {}".format(self.nginx_spec_path)
        underlay.check_call(cmd, host=config.k8s.kube_host)

        pods_start_time_after_cmd = self.get_nginx_pod_start_time(k8sclient)
        time.sleep(30)
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)

        assert pods_start_time == pods_start_time_after_cmd, (
            "pod's restarted. pods start time before rollout: \n{}\n "
            "pods start time after rollout: \n{}".format(
                pods_start_time,
                pods_start_time_after_cmd)
        )

    @pytest.mark.fail_snapshot
    @pytest.mark.snapshot_needed
    def test_daemonset_rollout_revision_negative_3(self, underlay, k8scluster,
                                                   config, show_step):
        """Test handling of negative values for --to-revision argument
            for kubectl rollout undo daemonset/<name>

        Scenario:
             1. Deploy k8s using fuel-ccp-installer
            2. Create a Deployment for Daemonset Upgrade controller
            3. Create a DaemonSet for nginx with image version 1_10 and
               update strategy RollingUpdate
            4. Wait until nginx pods are created and become 'ready'
            5. Check that the image version in the nginx pods is 1_10
               Check that the image version in the nginx daemonset is 1_10
            6. Rollback the nginx daemonset with float value revision
            7. Check that rollout was skipped and pods were not restarted
        Duration: 3000 seconds
        """

        # STEP #1
        show_step(1)
        k8sclient = k8scluster.api
        assert k8sclient.nodes.list() is not None, "Can not get nodes list"

        # STEP #2
        show_step(2)
        ds_controller_spec = self.get_ds_upgrade_controller_spec()
        k8sclient.deployments.create(body=ds_controller_spec)

        # STEP #3
        show_step(3)
        nginx_spec = self.get_nginx_spec()
        self.write_spec_to_yaml(nginx_spec, self.nginx_spec_path, underlay,
                                config)
        with underlay.yaml_editor(self.nginx_spec_path,
                                  host=config.k8s.kube_host) as editor:
            editor.content['spec']['template']['spec']['containers'][0][
                'image'] = self.from_nginx_image

        cmd = "kubectl create -f {}".format(self.nginx_spec_path)
        underlay.check_call(cmd, host=config.k8s.kube_host)

        # STEP #4
        show_step(4)
        time.sleep(3)
        self.wait_nginx_pods_ready(k8sclient)

        # STEP #5
        show_step(5)
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)

        # STEP #6,7
        show_step(6)
        show_step(7)
        pods_start_time = self.get_nginx_pod_start_time(k8sclient)

        with underlay.yaml_editor(self.nginx_spec_path,
                                  host=config.k8s.kube_host) as editor:
            editor.content['metadata']['annotations'][
                'daemonset.kubernetes.io/rollbackTo'] = "0.0"

        cmd = "kubectl apply -f {}".format(self.nginx_spec_path)
        underlay.check_call(cmd, host=config.k8s.kube_host)

        time.sleep(30)
        self.check_nginx_pods_image(k8sclient, self.from_nginx_image)
        self.check_nginx_ds_image(k8sclient, self.from_nginx_image)

        pods_start_time_after_cmd = self.get_nginx_pod_start_time(k8sclient)

        assert pods_start_time == pods_start_time_after_cmd, (
            "pod's restarted. pods start time before rollout: \n{}\n "
            "pods start time after rollout: \n{}".format(
                pods_start_time,
                pods_start_time_after_cmd)
        )
