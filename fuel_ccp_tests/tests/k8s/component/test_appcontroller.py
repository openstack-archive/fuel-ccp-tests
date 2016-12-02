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
import iso8601

from devops.helpers import helpers
from k8sclient.client import rest
import pytest
import yaml

from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import ext

LOG = logger.logger


class AppControllerResoucesStatus(object):
    """Helper class to check defined resources creation of AppController"""

    resources = [
        "dependency.appcontroller.k8s",
        "definition.appcontroller.k8s"
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

    def get_k8s_object(self, resource):
        resource_type, resource_name = resource.split('/')
        if resource_name is None:
            raise ValueError("Resource '{}' has wrong format".format(
                resource
            ))
        return self.__managers[resource_type]().get(name=resource_name)

    def register_linear_objects(self, list_resources=None):
        """Method to register check actions for each type of resources

        :param list_resources: list of strings "type/object"
        :raises: TypeError, KeyError, ValueError
        """
        # The following object will return function (checker) to run
        def obj_exists(resource):
            return lambda: self.get_k8s_object(resource) is not None
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
        creation_dates = []
        for item in self.__linear_order:
            resource_repr = getattr(item, '__resource_repr')
            helpers.wait(
                lambda: self._linear_check(item), timeout=300, interval=2,
                timeout_msg="{} creation timeout reached".format(resource_repr)
            )
            k8s_obj = self.get_k8s_object(resource_repr)
            creation_date = iso8601.parse_date(
                k8s_obj.metadata.creation_timestamp)
            creation_dates.append(creation_date)
            if len(creation_dates) > 1:
                assert creation_dates[-2] <= creation_dates[-1], (
                    "The order of linear objects is broken!")
        LOG.info("Linear check passed!")

    def thirdparty_resources(self):
        result = yaml.load(
            self.__ssh.check_call(
                "kubectl get thirdpartyresources -o yaml").stdout_str
        )
        return [item['metadata']['name'] for item in result['items']]


@pytest.mark.AppController
@pytest.mark.component_k8s
class TestAppController(object):

    kube_settings = {
        "hyperkube_image_repo": settings.HYPERKUBE_IMAGE_REPO,
        "hyperkube_image_tag": settings.HYPERKUBE_IMAGE_TAG,
        "searchdomains": settings.SEARCH_DOMAINS,
    }

    @pytest.mark.ac_linear_test
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.k8s_deployed)
    @pytest.mark.skipif(settings.AC_PATH is None,
                        reason="ApplicationController repo path is not set!")
    def test_linear(self, underlay, k8scluster, show_step):
        """Linear test of AppController work

        Scenario:
            1. Create AppController in k8s
            2. Wait until pod with AppController is Running
            3. Wait until required thirdparty resources are created
            4. Create dependencies from test
            5. Create definitions from test
            6. Run AppController to create defined resources
            7. Check if resources are created in expected order
        """
        node_name = underlay.node_names()[0]
        remote = underlay.remote(node_name=underlay.node_names()[0])
        ac_path = settings.AC_PATH
        ac_filepath = "%s/manifests/appcontroller.yaml" % ac_path
        LOG.info("Trying to read %s" % ac_filepath)
        with open(ac_filepath, 'r') as f:
            ac_pod = yaml.load(f.read())
        cmd_ac_run = "kubectl exec -i k8s-appcontroller ac-run"

        show_step(1)
        show_step(2)
        k8scluster.check_pod_create(body=ac_pod)

        # Load expected order to perform future checks
        expected_filepath = "%s/tests/linear/expected_order.yaml" % ac_path
        LOG.info(
            "Trying to read file with expected order %s" % expected_filepath)
        with open(expected_filepath) as f:
            expected_order = yaml.load(f.read())
            acr = AppControllerResoucesStatus(k8scluster.api, remote,
                                              expected_order)
        show_step(3)
        helpers.wait(
            lambda: set(acr.thirdparty_resources()).issubset(acr.resources),
            timeout=120, interval=2, timeout_msg="Resources creation timeout"
        )

        create_cmd_template = "echo '{}' | kubectl create -f -"

        show_step(4)
        deps_filename = "%s/tests/linear/dependencies.yaml" % ac_path
        LOG.info("Trying to read dependencies file %s" % deps_filename)
        with open(deps_filename) as f:
            deps_content = f.read()
        cmd = create_cmd_template.format(deps_content)
        helpers.wait(
            lambda: underlay.check_call(
                cmd, node_name=node_name, expected=[0, 1]
            ).exit_code == 0,
            timeout=30, interval=2, timeout_msg="Dependencies creation failed")

        show_step(5)
        defs_filename = "%s/tests/linear/definitions.yaml" % ac_path
        LOG.info("Trying to read definitions file %s" % defs_filename)
        with open(defs_filename) as f:
            defs_content = f.read()
        cmd = create_cmd_template.format(defs_content)
        underlay.check_call(cmd, node_name=node_name)

        show_step(6)
        underlay.check_call(cmd_ac_run, node_name=node_name)

        show_step(7)
        acr.linear_check()
