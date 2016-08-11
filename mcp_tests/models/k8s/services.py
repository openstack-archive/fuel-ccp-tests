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


from mcp_tests.models.k8s.base import K8sBaseResource
from mcp_tests.models.k8s.base import K8sBaseManager


class K8sService(K8sBaseResource):
    """docstring for K8sService"""

    def __repr__(self):
        return "<K8sService: %s>" % self.name

    @property
    def name(self):
        return self.metadata.name


class K8sServiceManager(K8sBaseManager):
    """docstring for K8sServiceManager"""

    resource_class = K8sService

    def _get(self, name, namespace=None, **kwargs):
        return self.api.read_namespaced_service(
            namespace=(namespace or self._namespace), name=name, **kwargs)

    def _list(self, namespace=None, **kwargs):
        return self.api.list_namespaced_service(
            namespace=(namespace or self._namespace), **kwargs)

    def _create(self, body, namespace=None, **kwargs):
        return self.api.create_namespaced_service(
            body, namespace=(namespace or self._namespace), **kwargs)

    def _replace(self, body, name, namespace=None, **kwargs):
        return self.api.replace_namespaced_service(
            body=body, namespace=(namespace or self._namespace), name=name,
            **kwargs)

    def _delete(self, body, name, namespace=None, **kwargs):
        return self.api.delete_namespaced_service(
            body=body, namespace=(namespace or self._namespace), name=name,
            **kwargs)

    def _deletecollection(self, namespace=None, **kwargs):
        return self.api.deletecollection_namespaced_service(
            namespace=(namespace or self._namespace), **kwargs)
