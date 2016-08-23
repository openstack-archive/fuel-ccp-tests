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


from fuel_ccp_tests.managers.k8s.base import K8sBaseResource
from fuel_ccp_tests.managers.k8s.base import K8sBaseManager


class K8sIngress(K8sBaseResource):
    """docstring for K8sIngress"""

    def __repr__(self):
        return "<K8sIngress: %s>" % self.name

    @property
    def name(self):
        return self.metadata.name


class K8sIngressManager(K8sBaseManager):
    """docstring for ClassName"""

    resource_class = K8sIngress

    def _get(self, name, namespace=None, **kwargs):
        namespace = namespace or self.namespace
        return self.api.read_namespaced_ingress(
            name=name, namespace=namespace, **kwargs)

    def _list(self, namespace=None, **kwargs):
        namespace = namespace or self.namespace
        return self.api.list_namespaced_ingress(
            namespace=namespace, **kwargs)

    def _full_list(self, **kwargs):
        return self.api.list_ingress(**kwargs)

    def _create(self, body, namespace=None, **kwargs):
        namespace = namespace or self.namespace
        return self.api.create_namespaced_ingress(
            body=body, namespace=namespace, **kwargs)

    def _replace(self, body, name, namespace=None, **kwargs):
        namespace = namespace or self.namespace
        return self.api.replace_namespaced_ingress(
            body=body, name=name, namespace=namespace, **kwargs)

    def _delete(self, body, name, namespace=None, **kwargs):
        namespace = namespace or self.namespace
        return self.api.delete_namespaced_ingress(
            body=body, name=name, namespace=namespace, **kwargs)

    def _deletecollection(self, namespace=None, **kwargs):
        namespace = namespace or self.namespace
        return self.api.deletecollection_namespaced_ingress(
            namespace=namespace, **kwargs)

    def full_list(self, *args, **kwargs):
        lst = self._full_list(*args, **kwargs)
        return [self.resource_class(self, item) for item in lst.items]
