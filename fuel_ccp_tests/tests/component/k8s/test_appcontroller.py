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

    def __init__(self, k8sclient, kube_ssh, expected_result=None):
        """
        :param k8sclient: fuel_ccp_tests.managers.k8s.cluster.K8sCluster
        :param kube_ssh: devops.helpers.ssh_client.SSHClient
        :param expected_result: list of strings in 'type/object_name' format
        """
        super(AppControllerResoucesStatus, self).__init__()
        self.__k8s = k8sclient
        self.__managers = {
            "job": lambda: self.__k8s.jobs,
            "pod": lambda: self.__k8s.pods,
            "replicaset": lambda: self.__k8s.replicasets,
            "service": lambda: self.__k8s.services,
        }
        self.__ssh = kube_ssh
        self.__linear_order = []
        self.register_linear_objects(expected_result)

    def register_linear_objects(self, list_resources=None):
        """Method to register check actions for each type of resources

        :param list_resources: list of strings "type/object"
        :raises: TypeError, KeyError, ValueError
        """
        # The following object will return function (checker) to run
        def obj_exists(resource):
            resource_type, resource_name = resource.split('/')
            if resource_name is None:
                raise ValueError("Resource '{}' has wrong format".format(
                    resource
                ))
            return (
                lambda: self.__managers[resource_type]().get(
                    name=resource_name) is not None)
        if list_resources:
            if not isinstance(list_resources, list):
                raise TypeError("list_resources must be a list instance!")
            result = []
            for resource in list_resources:
                try:
                    res_func = obj_exists(resource)
                    # To restore original name of object
                    setattr(res_func, '__resource_repr', resource)
                except KeyError:
                    raise KeyError(
                        "Resource '{}' has unsupported type!".format(resource))
                result.append(res_func)
            self.__linear_order = result

    def _linear_check(self, func):
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
                raise Exception("{} is already created!".format(resource_repr))
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
        for item in self.__linear_order:
            resource_repr = getattr(item, '__resource_repr')
            helpers.wait(
                lambda: self._linear_check(item), timeout=300, interval=2,
                timeout_msg="{} creation timeout reached".format(resource_repr)
            )

    def thirdparty_resources(self):
        result = yaml.load(
            self.__ssh.check_call(
                "kubectl get thirdpartyresources -o yaml").stdout_str
        )
        return [item['metadata']['name'] for item in result['items']]


@pytest.mark.AppController
@pytest.mark.component
class TestAppController(object):

    kube_settings = {
        "hyperkube_image_repo": settings.HYPERKUBE_IMAGE_REPO,
        "hyperkube_image_tag": settings.HYPERKUBE_IMAGE_TAG,
        "upstream_dns_servers": settings.UPSTREAM_DNS,
        "searchdomains": settings.SEARCH_DOMAINS,
        "use_hyperkube_cni": str("true"),
    }

    @pytest.mark.ac_linear_test
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.skipif(settings.AC_REPO == "",
                        reason="ApplicationController repo is not set!")
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
            acr = AppControllerResoucesStatus(k8scluster.api, remote,
                                              expected_order)
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
