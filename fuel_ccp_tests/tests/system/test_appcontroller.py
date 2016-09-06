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
from k8sclient.client import rest
import yaml

import base_test
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import ext

LOG = logger.logger


class AppControllerResoucesStatus(object):
    """Helper class to check defined resources creation of AppController"""

    resources = [
        "dependency.appcontroller.k8s1",
        "definition.appcontroller.k8s2"
    ]

    def __init__(self, expected_result, k8sclient, kube_ssh):
        """
        :param expected_result: list of strings in 'type/object_name' format
        :param k8sclient: fuel_ccp_tests.managers.k8s.cluster.K8sCluster
        """
        super(AppControllerResoucesStatus, self).__init__()
        self.__k8s = k8sclient
        self.__order = self._register_objects(expected_result)
        self.__ssh = kube_ssh

    def _register_objects(self, list_resources):
        """Method to register check actions for each type of resources

        :param list_resources: list of strings "type/object"
        """
        # The following object will return function (checker) to run
        k8s_objects_mapping = {
            "pod": lambda x: (
                lambda: self.__k8s.pods.get(name=x) is not None
            ),
            "job": lambda x: (
                lambda: self.__k8s.jobs.get(name=x) is not None),
            "service": lambda x: (
                lambda: self.__k8s.services.get(name=x) is not None),
            "replicaset": lambda x: (
                lambda: self.__k8s.replicasets.get(name=x) is not None)
        }
        result = []
        for resource in list_resources:
            resource_type, resource_name = resource.split('/')
            try:
                res_func = k8s_objects_mapping[resource_type](resource_name)
                # To restore original name of object
                setattr(res_func, '__resource_repr', resource)
            except KeyError:
                raise KeyError("{} resource type is not supported yet!".format(
                    resource_type))
            result.append(res_func)
        return result

    def _check(self, func):
        """Action to run check

        :param func: function to run
        """
        # Each function must be created with this attribute
        resource_repr = getattr(func, '__resource_repr')
        # Additional flag to detect if object has already created
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

    def linear_check(self):
        """Action to wait until all checks are done
        Each check has own timeout equals 300 secs"""
        for item in self.__order:
            resource_repr = getattr(item, '__resource_repr')
            helpers.wait(
                lambda: self._check(item), timeout=300, interval=2,
                timeout_msg="{} creation timeout reached".format(resource_repr)
            )

    def thirdparty_resources(self):
        return yaml.load(
            self.__ssh.check_call(
                "kubectl get thirdpartyresources -o yaml").stdout_str
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

    @pytest.mark.ac_linear_test
    @pytest.mark.snapshot_needed
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.fail_snapshot
    def test_linear(self, underlay, k8scluster):
        """Linear test of AppController work

        Scenario:
            1. Get AppController source on master node
            2. Create AppController in k8s
            3. Wait until pod with AppController is Running
            4. Wait until required thirdparty resources are created
            5. Create dependencies from test
            6. Create definitions from test
            7. Run AppController to create defined resources
            8. Check if resources are created in expected order
        """
        node_name = underlay.node_names()[0]
        remote = underlay.remote(node_name=underlay.node_names()[0])
        cmd_ac_run = "kubectl exec -i k8s-appcontroller ac-run"

        # Install additional software if it's needed
        underlay.sudo_check_call(
            cmd="which unzip || apt-get install unzip",
            node_name=node_name)

        cmd = """wget -qO ac.zip {url} &&
        unzip -qq ac && mv k8s-AppController-{commit} k8s-AppController &&
        cd k8s-AppController && pwd""".format(
            url=settings.AC_ZIP_URL, commit=settings.AC_COMMIT)

        LOG.info("1. Get AppController source on master node")
        ac_path = underlay.check_call(
            cmd, node_name=node_name).stdout_str

        LOG.info("2. Create AppController in k8s")
        underlay.check_call(
            "kubectl create -f {}/manifests/appcontroller.yaml".format(
                ac_path),
            node_name=node_name)

        LOG.info("3. Wait until pod with AppController is Running")
        k8scluster.wait_pod_phase(
            pod_name="k8s-appcontroller", phase="Running", timeout=300)

        # Load expected order to perform future checks
        file_name = "{}/tests/linear/expected_order.yaml".format(ac_path)
        with remote.open(file_name) as f:
            expected_order = yaml.load(f.read())
            acr = AppControllerResoucesStatus(expected_order, k8scluster.api,
                                              remote)
        LOG.info("4. Wait until required thirdparty resources are created")
        helpers.wait(
            lambda: set(acr.thirdparty_resources()).issubset(acr.resources),
            timeout=120, interval=2, timeout_msg="Resources creation timeout"
        )

        LOG.info("5. Create dependencies from test")
        cmd = "kubectl create -f {}/tests/linear/dependencies.yaml".format(
            ac_path)
        helpers.wait(
            lambda: underlay.check_call(
                cmd, node_name=node_name, expected=[0, 1]
            ).exit_code == 0,
            timeout=30, interval=2, timeout_msg="Dependencies creation failed")

        LOG.info("6. Create definitions from test")
        underlay.check_call(
            "kubectl create -f {}/tests/linear/definitions.yaml".format(
                ac_path),
            node_name=node_name)

        LOG.info("7. Run AppController to create defined resources")
        underlay.check_call(cmd_ac_run, node_name=node_name)

        LOG.info("8. Check if resources are created in expected order")
        acr.linear_check()
