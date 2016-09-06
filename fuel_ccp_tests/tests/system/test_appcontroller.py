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

    def k8s_obj_successful(self, k8sclient, obj):
        pods = k8sclient.get_pod_phase
        services = k8sclient.services
        replicas = k8sclient.replicasets
        jobs = k8sclient.jobs
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
        k8sclient = k8scluster.api
        remote = underlay.remote(node_name=underlay.node_names()[0])
        podphase = (
            lambda x: k8sclient.get_pod_phase(pod_name=x)
        )
        cmd = "wget -O k8s-AppController.zip {url}".format(settings.AC_ZIP_URL)
        cmd = cmd + " && unzip k8s-AppController.zip"
        cmd_ac_run = "kubectl exec -i k8s-appcontroller ac-run"
        tests_folder = "tests/linear"
        remote.execute(
            cmd, verbose=True
        )
        remote.execute(
            "kubectl create -f k8s-AppController/manifests/dependencies.json",
            verbose=True
        )
        remote.execute(
            "kubectl create -f k8s-AppController/manifests/resdefs.json",
            verbose=True
        )
        remote.execute(
            "kubectl create -f k8s-AppController/manifests/appcontroller.yaml",
            verbose=True
        )
        helpers.wait(
            lambda: podphase("k8s-appcontroller") == "Running",
            interval=2, timeout=120,
            timeout_msg="AppController creating timeout reached"
        )
        remote.execute(cmd_ac_run, verbose=True)
        LOG.info(
            "Sleep for 30 seconds to get app-controller time"
            "for creating internal resources")
        time.sleep(30)
        with remote.open('k8s-AppController/{}/expected_order.yaml') as f:
            expected_order = yaml.load(f.read())
        remote.execute(
            "kubectl create -f k8s-AppController/{}/dependencies.yaml".format(
                tests_folder
            ),
            verbose=True
        )
        remote.execute(
            "kubectl create -f k8s-AppController/{}/definitions.yaml".format(
                tests_folder
            ),
            verbose=True
        )
        remote.execute(cmd_ac_run, verbose=True)
        for obj in expected_order:
            LOG.info("Checking {} success")
            helpers.wait(
                lambda: self.k8s_object_successful(k8sclient, obj),
                interval=2, timeout=300,
                timeout_msg="Object {} success timeout reached".format(
                    obj
                )
            )
            LOG.info("Object {} has successful state")
