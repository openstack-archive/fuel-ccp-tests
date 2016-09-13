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

import yaml

from devops.helpers.helpers import wait

from fuel_ccp_tests import logger

LOG = logger.logger
LOG.addHandler(logger.console)


class SystemBaseTest(object):
    """SystemBaseTest contains setup/teardown for environment creation"""

    def calico_ipip_exists(self, underlay):
        """Check if ipip is in calico pool config

        :param underlay: fuel_ccp_tests.managers.UnderlaySSHManager
        """
        cmd = "calicoctl pool show | grep ipip"
        for node_name in underlay.node_names():
            underlay.sudo_check_call(cmd, node_name=node_name)

    def required_images_exists(self, node_name, underlay, required_images):
        """Check if there are all base containers on node

        :param node_name: string
        :param underlay: fuel_ccp_tests.managers.UnderlaySSHManager
        :param required_images: list
        """
        cmd = "docker ps --no-trunc --format '{{.Image}}'"
        result = underlay.sudo_check_call(cmd, node_name=node_name)
        images = [x.split(":")[0] for x in result['stdout']]
        assert set(required_images) < set(images),\
            "Running containers check failed on node '{}'".format(node_name)

    def required_images_version_exists(self, node_name, underlay,
                                       required_images_version):
        """Check if there are all base containers on node

        :param node_name: string
        :param underlay: fuel_ccp_tests.managers.UnderlaySSHManager
        :param required_images_version: dict, {<image_name_part>: <tag>, }
        """
        cmd = "docker images --no-trunc --format '{{.Repository}} {{.Tag}}'"
        result = underlay.sudo_check_call(cmd, node_name=node_name)
        images = dict(x.split() for x in result.stdout)
        err_msg = ''
        for name in required_images_version.keys():
            img_name = [x for x in images.keys() if name in x]
            if not img_name:
                err_msg += "Image for '{0}' not found\n".format(name)
            elif len(img_name) > 1:
                err_msg += "Found more than one image for '{0}'\n".format(name)
            elif images[img_name[0]] != required_images_version[name]:
                err_msg += (
                    "Image for '{0}' has version {1} while expecting version "
                    "{2}\n".format(images[img_name[0]],
                                   required_images_version[name])
                )
        assert err_msg == '',\
            err_msg + "Expected: {}\nActually: {}\n".format(
                required_images_version, images)

    def required_packages_version_exists(self, node_name, underlay,
                                         required_packages_version):
        """Check if there are all base containers on node

        :param node_name: string
        :param underlay: fuel_ccp_tests.managers.UnderlaySSHManager
        :param required_packages_version: dict,
            {<command_to_get_version>: <version_starts_with>, }
        """
        err_msg = ''
        for cmd in required_packages_version.keys():
            result = underlay.sudo_check_call(cmd, node_name=node_name)
            if not result.stdout_str.startswith(
                    str(required_packages_version[cmd])):
                err_msg += ("Command '{0}' returned version {1} while "
                            "expecting version {2}\n"
                            .format(result.stdout_str,
                                    required_packages_version[cmd]))

        assert err_msg == '', err_msg

    def check_required_versions(self, underlay, node_name, kube_settings):
        """Check that images in docker and packages on the 'node_name'
           have expected versions.
        """
        required_images_version = {
            kube_settings["hyperkube_image_repo"]: kube_settings[
                "hyperkube_image_tag"],
        }

        # If etcd installed in docker, let's check the etcd image tag
        if kube_settings['etcd_deployment_type'] == 'docker':
            required_images_version.update(
                {kube_settings["etcd_image_repo"]: kube_settings[
                    "etcd_image_tag"]}
            )

        self.required_images_version_exists(node_name, underlay,
                                            required_images_version)

        # dict of commands and expected output
        required_packages_version = {
            "docker version -f '{{.Client.Version}}'": kube_settings[
                "docker_version"],
            "kubectl --version | awk '{print $2}'": kube_settings[
                "kube_version"],
        }

        # If etcd installed on host, it should be checked as a package
        if kube_settings['etcd_deployment_type'] == 'host':
            required_packages_version.update(
                {"etcdctl --version | grep 'etcdctl version:' | "
                 "awk '{print \"v\"$NF}'": kube_settings["etcd_image_tag"]}
            )

        self.required_packages_version_exists(node_name, underlay,
                                              required_packages_version)

    def check_list_required_images(self, underlay, required_images):
        """Check running containers on each node

        :param underlay: fuel_ccp_tests.managers.UnderlaySSHManager
        :param required_images: list
        """
        LOG.info("Check that required containers exist")
        for node_name in underlay.node_names():
            self.required_images_exists(node_name, underlay, required_images)

    def check_pod_create(self, body, k8sclient, timeout=300, interval=5):
        """Check creating sample pod

        :param k8s_pod: V1Pod
        :param k8sclient: K8sCluster
        :rtype: V1Pod
        """
        LOG.info("Creating pod in k8s cluster")
        LOG.debug(
            "POD spec to create:\n{}".format(
                yaml.dump(body, default_flow_style=False))
        )
        LOG.debug("Timeout for creation is set to {}".format(timeout))
        LOG.debug("Checking interval is set to {}".format(interval))
        pod = k8sclient.pods.create(body=body)
        pod.wait_running(timeout=300, interval=5)
        LOG.info("Pod '{}' is created".format(pod.metadata.name))
        return k8sclient.pods.get(name=pod.metadata.name)

    @staticmethod
    def wait_pod_deleted(k8sclient, podname, timeout=60, interval=5):
        wait(
            lambda: podname not in [pod.name for pod in k8sclient.pods.list()],
            timeout=timeout,
            interval=interval,
            timeout_msg="Pod deletion timeout reached!"
        )

    @staticmethod
    def check_pod_delete(k8s_pod, k8sclient, timeout=300, interval=5):
        """Deleting pod from k8s

        :param k8s_pod: fuel_ccp_tests.managers.k8s.nodes.K8sNode
        :param k8sclient: fuel_ccp_tests.managers.k8s.cluster.K8sCluster
        """
        LOG.info("Deleting pod '{}'".format(k8s_pod.name))
        LOG.debug("Pod status:\n{}".format(k8s_pod.status))
        LOG.debug("Timeout for deletion is set to {}".format(timeout))
        LOG.debug("Checking interval is set to {}".format(interval))
        k8sclient.pods.delete(body=k8s_pod, name=k8s_pod.name)
        SystemBaseTest.wait_pod_deleted(k8sclient, k8s_pod.name, timeout,
                                        interval)
        LOG.debug("Pod '{}' is deleted".format(k8s_pod.name))

    @staticmethod
    def check_service_create(body, k8sclient):
        """Check creating k8s service

        :param body: dict, service spec
        :param k8sclient: K8sCluster object
        :rtype: K8sService object
        """
        LOG.info("Creating service in k8s cluster")
        LOG.debug(
            "Service spec to create:\n{}".format(
                yaml.dump(body, default_flow_style=False))
        )
        service = k8sclient.services.create(body=body)
        LOG.info("Service '{}' is created".format(service.metadata.name))
        return k8sclient.services.get(name=service.metadata.name)

    @staticmethod
    def check_ds_create(body, k8sclient):
        """Check creating k8s DaemonSet

        :param body: dict, DaemonSet spec
        :param k8sclient: K8sCluster object
        :rtype: K8sDaemonSet object
        """
        LOG.info("Creating DaemonSet in k8s cluster")
        LOG.debug(
            "DaemonSet spec to create:\n{}".format(
                yaml.dump(body, default_flow_style=False))
        )
        ds = k8sclient.daemonsets.create(body=body)
        LOG.info("DaemonSet '{}' is created".format(ds.metadata.name))
        return k8sclient.daemonsets.get(name=ds.metadata.name)

    def check_number_kube_nodes(self, underlay, k8sclient):
        """Check number of slaves"""
        LOG.info("Check number of nodes")
        k8s_nodes = k8sclient.nodes.list()
        node_names = underlay.node_names()
        assert len(k8s_nodes) == len(node_names),\
            "Check number k8s nodes failed!"

    def check_etcd_health(self, underlay):
        node_names = underlay.node_names()
        cmd = "etcdctl cluster-health | grep -c 'got healthy result'"

        etcd_nodes = underlay.sudo_check_call(
            cmd, node_name=node_names[0])['stdout'][0]
        assert int(etcd_nodes) == len(node_names),\
            "Number of etcd nodes is {0}," \
            " should be {1}".format(int(etcd_nodes), len(node_names))

    def create_env_snapshot(self, name, hardware, description=None):
        hardware.create_snapshot(name, description=description)
