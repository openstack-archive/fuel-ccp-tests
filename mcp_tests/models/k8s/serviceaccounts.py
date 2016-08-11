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


class K8sServiceAccount(K8sBaseResource):
    """docstring for K8sServiceAccount"""

    def __repr__(self):
        return "<K8sServiceAccount: %s>" % self.name

    @property
    def name(self):
        return self.metadata.name


class K8sServiceAccountManager(K8sBaseManager):
    """docstring for K8sServiceAccountManager"""

    resource_class = K8sServiceAccount

    def _get(self, name, **kwargs):
        return self.api.read_namespaced_service_account(name=name, **kwargs)

    def _list(self, **kwargs):
        return self.api.list_namespaced_service_account(**kwargs)

    def _create(self, body, **kwargs):
        return self.api.create_namespaced_service_account(body=body, **kwargs)

    def _replace(self, body, name, **kwargs):
        return self.api.replace_namespaced_service_account(
            body=body, name=name, **kwargs)

    def _delete(self, body, name, **kwargs):
        return self.api.delete_namespaced_service_account(
            body=body, name=name, **kwargs)

    def _deletecollection(self, **kwargs):
        return self.api.deletecollection_namespaced_service_account(**kwargs)
