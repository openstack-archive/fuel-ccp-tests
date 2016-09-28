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

from devops.helpers import helpers

from fuel_ccp_tests.managers.k8s.base import K8sBaseResource
from fuel_ccp_tests.managers.k8s.base import K8sBaseManager


class K8sPod(K8sBaseResource):
    """docstring for K8sPod"""

    def __repr__(self):
        return "<K8sPod: %s>" % self.name

    @property
    def name(self):
        return self.metadata.name

    @property
    def phase(self):
        return self.status.phase

    def wait_phase(self, phase, timeout=60, interval=5):
        """Wait phase of pod_name from namespace while timeout

        :param list or str: phase
        :param int: timeout

        :rtype: None
        """
        if isinstance(phase, str):
            phase = [phase]

        def check():
            self._add_details(self._manager.get(name=self.name))
            return self.phase in phase

        helpers.wait(check, timeout=timeout, interval=interval,
                     timeout_msg='Timeout waiting({timeout}s), pod {pod_name} '
                                 'is not in "{phase}" phase'.format(
                                     timeout=timeout,
                                     pod_name=self.name,
                                     phase=phase))

    def wait_running(self, timeout=60, interval=5):
        self.wait_phase(['Running'], timeout=timeout, interval=interval)


class K8sPodManager(K8sBaseManager):
    """docstring for ClassName"""

    resource_class = K8sPod

    def _get(self, name, namespace=None, **kwargs):
        namespace = namespace or self.namespace
        return self.api.read_namespaced_pod(
            name=name, namespace=namespace, **kwargs)

    def _list(self, namespace=None, **kwargs):
        namespace = namespace or self.namespace
        return self.api.list_namespaced_pod(namespace=namespace, **kwargs)

    def _create(self, body, namespace=None, **kwargs):
        namespace = namespace or self.namespace
        return self.api.create_namespaced_pod(
            body=body, namespace=namespace, **kwargs)

    def _replace(self, body, name, namespace=None, **kwargs):
        namespace = namespace or self.namespace
        return self.api.replace_namespaced_pod(
            body=body, name=name, namespace=namespace, **kwargs)

    def _delete(self, body, name, namespace=None, **kwargs):
        namespace = namespace or self.namespace
        # NOTE: the following two lines should be deleted after
        # serialization is fixed in python-k8sclient
        if isinstance(body, self.resource_class):
            body = body.swagger_types
        return self.api.delete_namespaced_pod(
            body=body, name=name, namespace=namespace, **kwargs)

    def _deletecollection(self, namespace=None, **kwargs):
        namespace = namespace or self.namespace
        return self.api.deletecollection_namespaced_pod(
            namespace=namespace, **kwargs)

    def full_list(self, *args, **kwargs):
        lst = self._full_list(*args, **kwargs)
        return [self.resource_class(self, item) for item in lst.items]

    def _full_list(self, **kwargs):
        return self.api.list_pod(**kwargs)
