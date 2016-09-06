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
        self.__expected_result = expected_result
        self.__order = self._register_objects(expected_result)
        self.__result_list = []

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
        try:
            result = func()
            resource_repr = getattr(func, '__resource_repr')
            if not getattr(func, '__to_be_created', False):
                raise Exception("{} is already created!".resource_repr)
            LOG.info("{} is created".format(resource_repr))
            self.__result_list.append(resource_repr)
        except rest.ApiException as err:
            LOG.debug(err)
            setattr(func, '__to_be_created', True)
            result = False
        return result

    def perform_checks(self):
        for item in self.__order:
            helpers.wait(lambda: self._check(item), timeout=300, interval=2)

    def proceed(self):
        self.perform_checks()
        return self.__expected_result == self.__result_list


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
            acr = AppControllerResoucesStatus(expected_order, k8scluster.api)
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
        if acr.proceed():
            LOG.info("All objects creates as in expected order!")
        else:
            pytest.xfail("Test failed! Seems like objects have created in "
                         "unexpected order!")
