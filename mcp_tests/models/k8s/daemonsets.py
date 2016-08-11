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


class K8sDaemonSet(K8sBaseResource):
    """docstring for K8sDaemonSet"""

    def __repr__(self):
        return "<K8sDaemonSet: %s>" % self.name

    @property
    def name(self):
        return self.metadata.name


class K8sDaemonSetManager(K8sBaseManager):
    """docstring for ClassName"""

    resource_class = K8sDaemonSet

    def _get(self, name, **kwargs):
        return self.api.read_namespaced_daemon_set(name=name, **kwargs)

    def _list(self, **kwargs):
        return self.api.list_namespaced_daemon_set(**kwargs)

    def _full_list(self, **kwargs):
        return self.api.list_daemon_set(**kwargs)

    def _create(self, body, **kwargs):
        return self.api.create_namespaced_daemon_set(body=body, **kwargs)

    def _replace(self, body, name, **kwargs):
        return self.api.replace_namespaced_daemon_set(
            body=body, name=name, **kwargs)

    def _delete(self, body, name, **kwargs):
        return self.api.delete_namespaced_daemon_set(
            body=body, name=name, **kwargs)

    def _deletecollection(self, **kwargs):
        return self.api.deletecollection_namespaced_daemon_set(**kwargs)

    def full_list(self, *args, **kwargs):
        lst = self._full_list(*args, **kwargs)
        return [self.resource_class(self, item) for item in lst.items]
