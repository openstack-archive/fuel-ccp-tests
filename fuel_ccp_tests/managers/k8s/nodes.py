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


class K8sNode(K8sBaseResource):
    """docstring for ClassName"""

    def __repr__(self):
        return "<K8sNode: %s>" % self.name

    @property
    def name(self):
        return self.metadata.name

    @property
    def labels(self):
        return self.metadata.labels

    @labels.setter
    def labels(self, labels):
        current_labels = {
            label: None for label in self.labels
        }
        current_labels.update(labels)
        self.add_labels(labels=current_labels)

    def add_labels(self, labels):
        if not isinstance(labels, dict):
            raise TypeError("labels must be a dict!")
        body = {
            "metadata":
            {
                "labels": labels
            }
        }
        self._add_details(self._manager.update(body=body, name=self.name))

    def remove_labels(self, list_labels):
        labels = {label: None for label in list_labels}
        self.add_labels(labels=labels)


class K8sNodeManager(K8sBaseManager):
    """docstring for ClassName"""

    resource_class = K8sNode

    def _get(self, name, **kwargs):
        return self.api.read_namespaced_node(name=name, **kwargs)

    def _list(self, **kwargs):
        return self.api.list_namespaced_node(**kwargs)

    def _create(self, body, **kwargs):
        return self.api.create_namespaced_node(body=body, **kwargs)

    def _replace(self, body, name, **kwargs):
        return self.api.replace_namespaced_node(body=body, name=name, **kwargs)

    def _delete(self, body, name, **kwargs):
        return self.api.delete_namespaced_node(body=body, name=name, **kwargs)

    def _deletecollection(self, **kwargs):
        return self.api.deletecollection_namespaced_node(**kwargs)

    def update(self, body, name, **kwargs):
        return self.api.patch_namespaced_node(body=body, name=name, **kwargs)
