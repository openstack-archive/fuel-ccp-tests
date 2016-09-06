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
import time

from devops.helpers import helpers
import yaml

import base_test
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import ext

LOG = logger.logger


@pytest.mark.AppController
class TestAppController(base_test.SystemBaseTest):

    kube_settings = {
        "hyperkube_image_repo":
        "artifactory.mcp.mirantis.net:5002/hyperkube-amd64",
        "hyperkube_image_tag": "v1.4.0-beta.0-1-gd80ff_64",
        "upstream_dns_servers": ["172.18.80.135", "172.18.16.10"],
        "nameservers": ["8.8.8.8", "172.18.80.136"],
        "searchdomains": ["ccp.svc.cluster.local", "mcp.mirantis.net",
                          "mirantis.net"],
        "use_hyperkube_cni": str("true"),
    }

    def k8s_obj_successful(self, k8scluster, obj):
        pods = k8scluster.get_pod_phase
        services = k8scluster.api.services
        replicas = k8scluster.api.replicasets
        jobs = k8scluster.api.jobs
        successful = {
            "pod": (
                lambda x: pods(pod_name=x) == "Running"
            ),
            "job": (
                lambda x: jobs.get(name=x).status.succeeded == 1
            ),
            "service": (
                lambda x: services.get(name=x).spec.type == "ClusterIP"),
            "replicaset": (
                lambda x: replicas.get(name=x).status.replicas ==
                replicas.get(name=x).status.fully_labeled_replicas)
        }
        obj_type, obj_name = obj.split('/')
        return successful[obj_type](obj_name)

    @pytest.mark.ac_linear_test_manual
    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    def test_linear_manually(self, underlay, k8scluster):
        """Doc string"""
        node_name = underlay.node_names()[0]
        remote = underlay.remote(node_name=underlay.node_names()[0])
        underlay.sudo_check_call(
            cmd="which unzip || apt-get install unzip",
            node_name=node_name)
        podphase = (
            lambda x: k8scluster.get_pod_phase(pod_name=x)
        )
        cmd_ac_run = "kubectl exec -i k8s-appcontroller ac-run"
        cmd = """wget -O ac.zip {url} &&
        unzip ac && mv k8s-AppController-{commit} k8s-AppController""".format(
            url=settings.AC_ZIP_URL, commit=settings.AC_COMMIT)
        tests_folder = "tests/linear"
        underlay.check_call(
            cmd, node_name=node_name, verbose=True)
        underlay.check_call(
            "kubectl create -f k8s-AppController/manifests/dependencies.json",
            node_name=node_name, verbose=True
        )
        underlay.check_call(
            "kubectl create -f k8s-AppController/manifests/resdefs.json",
            node_name=node_name, verbose=True
        )
        underlay.check_call(
            "kubectl create -f k8s-AppController/manifests/appcontroller.yaml",
            node_name=node_name, verbose=True
        )
        LOG.info("Wait until k8s-appcontroller is created")
        helpers.wait(
            lambda: podphase("k8s-appcontroller") == "Running",
            interval=2, timeout=120,
            timeout_msg="AppController creating timeout reached"
        )
        underlay.check_call(cmd_ac_run, node_name=node_name, verbose=True)
        LOG.info(
            "Sleep for 9 seconds to get app-controller time "
            "for creating internal resources")
        time.sleep(9)
        file_name = "/home/vagrant/k8s-AppController/{}/expected_order.yaml"
        with remote.open(file_name.format(tests_folder)) as f:
            expected_order = yaml.load(f.read())
        underlay.check_call(
            "kubectl create -f k8s-AppController/{}/dependencies.yaml".format(
                tests_folder
            ),
            node_name=node_name, verbose=True
        )
        underlay.check_call(
            "kubectl create -f k8s-AppController/{}/definitions.yaml".format(
                tests_folder
            ),
            node_name=node_name, verbose=True
        )
        underlay.check_call(cmd_ac_run, node_name=node_name, verbose=True)
        for obj in expected_order:
            time.sleep(3)
            LOG.info("Checking {} success".format(obj))
            helpers.wait(
                lambda: self.k8s_obj_successful(k8scluster, obj),
                interval=2, timeout=300,
                timeout_msg="Object {} success timeout reached".format(
                    obj
                )
            )
            LOG.info("Object {} has successful state".format(obj))
