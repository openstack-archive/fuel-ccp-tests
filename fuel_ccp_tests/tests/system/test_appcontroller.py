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

from devops.helpers import helpers
import yaml
from k8sclient.client import rest

import base_test
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import ext

LOG = logger.logger


class AppControllerResoucesStatus(object):
    def __init__(self, expected_result, k8sclient):
        super(AppControllerResoucesStatus, self).__init__()
        self.__k8s = k8sclient
        self.__order = self._register_objects(expected_result)

    def _register_objects(self, list_resources):
        api = self.__k8s
        k8s_objects_mapping = {
            "pod": lambda x: (
                lambda: api.pods.get(name=x) is not None
            ),
            "job": lambda x: (
                lambda: api.jobs.get(name=x) is not None),
            "service": lambda x: (
                lambda: api.services.get(name=x) is not None),
            "replicaset": lambda x: (
                lambda: api.replicasets.get(name=x) is not None)
        }
        result = []
        for resource in list_resources:
            resource_type, resource_name = resource.split('/')
            try:
                res_func = k8s_objects_mapping[resource_type](resource_name)
                setattr(res_func, '__resource_repr', resource)
            except KeyError:
                raise KeyError("{} resource type is not supported yet!".format(
                    resource_type))
            result.append(res_func)
        return result

    def _check(self, func):
        resource_repr = getattr(func, '__resource_repr')
        must_created = getattr(func, '__to_be_created', None)
        try:
            result = func()
            if must_created is None:
                raise Exception("{} is already created!".resource_repr)
            LOG.info("{} is created".format(resource_repr))
        except rest.ApiException as err:
            LOG.debug(err)
            if must_created is None:
                setattr(func, '__to_be_created', True)
                LOG.info("{} should be created".format(resource_repr))
            result = False
        return result

    def perform_checks(self):
        for item in self.__order:
            resource_repr = getattr(item, '__resource_repr')
            helpers.wait(
                lambda: self._check(item), timeout=300, interval=2,
                timeout_msg="{} creation timeout reached".format(resource_repr)
            )


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

    @pytest.mark.ac_linear_test_manual
    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    def test_linear_manually(self, underlay, k8scluster):
        """Linear test of AppController work

        Scenario:
            1. Get AppController source on master node
            2. Create thirdparty dependencies in k8s
            3. Create thirdparty resource definitions in k8s
            4. Create AppController in k8s
            5. Wait until pod with AppController is Running
            6. Run AppController to create required resources
            7. Create dependencies from test
            8. Create definitions from test
            9. Run AppController to create defined resources
            10. Check if resources are created in expected order
        """
        node_name = underlay.node_names()[0]
        remote = underlay.remote(node_name=underlay.node_names()[0])
        # Install additional software if it's needed
        underlay.sudo_check_call(
            cmd="which unzip || apt-get install unzip",
            node_name=node_name)
        tests_folder = "tests/linear"
        cmd_ac_run = "kubectl exec -i k8s-appcontroller ac-run"
        cmd = """wget -O ac.zip {url} &&
        unzip ac && mv k8s-AppController-{commit} k8s-AppController""".format(
            url=settings.AC_ZIP_URL, commit=settings.AC_COMMIT)
        LOG.info("1. Get AppController source on master node")
        underlay.check_call(
            cmd, node_name=node_name)
        LOG.info("2. Create thirdparty dependencies in k8s")
        underlay.check_call(
            "kubectl create -f k8s-AppController/manifests/dependencies.json",
            node_name=node_name
        )
        LOG.info("3. Create thirdparty resource definitions in k8s")
        underlay.check_call(
            "kubectl create -f k8s-AppController/manifests/resdefs.json",
            node_name=node_name
        )
        LOG.info("4. Create AppController in k8s")
        underlay.check_call(
            "kubectl create -f k8s-AppController/manifests/appcontroller.yaml",
            node_name=node_name
        )
        LOG.info("5. Wait until pod with AppController is Running")
        k8scluster.wait_pod_phase(
            pod_name="k8s-appcontroller", phase="Running", timeout=300)
        LOG.info("6. Run AppController to create required resources")
        underlay.check_call(cmd_ac_run, node_name=node_name)
        file_name = "/home/vagrant/k8s-AppController/{}/expected_order.yaml"
        with remote.open(file_name.format(tests_folder)) as f:
            expected_order = yaml.load(f.read())
            acr = AppControllerResoucesStatus(expected_order, k8scluster.api)
        LOG.info("7. Create dependencies from test")
        cmd = "kubectl create -f k8s-AppController/{}/dependencies.yaml"
        helpers.wait(
            lambda: underlay.check_call(
                cmd.format(tests_folder),
                node_name=node_name,
                expected=[0, 1]
            ).exit_code == 0,
            timeout=30, interval=2, timeout_msg="Dependencies creation failed"
        )
        LOG.info("8. Create definitions from test")
        underlay.check_call(
            "kubectl create -f k8s-AppController/{}/definitions.yaml".format(
                tests_folder
            ),
            node_name=node_name
        )
        LOG.info("9. Run AppController to create defined resources")
        underlay.check_call(cmd_ac_run, node_name=node_name)
        LOG.info("10. Check if resources are created in expected order")
        acr.perform_checks()
