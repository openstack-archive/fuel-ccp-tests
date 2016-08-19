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


class K8sPersistentVolume(K8sBaseResource):
    """docstring for K8sPersistentVolume"""

    def __repr__(self):
        return "<K8sPersistentVolume: %s>" % self.name

    @property
    def name(self):
        return self.metadata.name


class K8sPersistentVolumeManager(K8sBaseManager):
    """docstring for ClassName"""

    resource_class = K8sPersistentVolume

    def _get(self, name, **kwargs):
        return self.api.read_namespaced_persistent_volume(
            name=name, **kwargs)

    def _list(self, **kwargs):
        return self.api.list_namespaced_persistent_volume(
            **kwargs)

    def _create(self, body, **kwargs):
        return self.api.create_namespaced_persistent_volume(
            body, **kwargs)

    def _replace(self, body, name, **kwargs):
        return self.api.replace_namespaced_persistent_volume(
            body=body, name=name, **kwargs)

    def _delete(self, body, name, **kwargs):
        return self.api.delete_namespaced_persistent_volume(
            body=body, name=name, **kwargs)

    def _deletecollection(self, **kwargs):
        return self.api.deletecollection_namespaced_persistent_volume(
            **kwargs)
