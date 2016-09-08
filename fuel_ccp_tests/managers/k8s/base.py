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


class K8sBaseResource(object):
    """docstring for K8sBaseResource"""

    def __init__(self, manager, data):
        self._manager = manager
        self._data = data
        self._add_details(data)

    def __repr__(self):
        reprkeys = sorted(k
                          for k in self.__dict__.keys()
                          if k[0] != '_' and
                          k not in ['manager'])
        info = ", ".join("%s=%s" % (k, getattr(self, k)) for k in reprkeys)
        return "<%s %s>" % (self.__class__.__name__, info)

    @property
    def api_version(self):
        return self._data.api_version

    def _add_details(self, data):
        for k in [k for k in dir(data)
                  if not any((k.startswith('_'), k in ('to_dict', 'to_str')))]:
            try:
                setattr(self, k, getattr(data, k))
            except AttributeError:
                # In this case we already defined the attribute on the class
                pass

    def __eq__(self, other):
        if not isinstance(other, K8sBaseResource):
            return NotImplemented
        # two resources of different types are not equal
        if not isinstance(other, self.__class__):
            return False
        return self._info == other._info


class K8sBaseManager(object):

    resource_class = None

    def __init__(self, api, namespace):
        self._api = api
        self._namespace = namespace
        self._raw = None

    @property
    def api(self):
        return self._api

    @property
    def namespace(self):
        return self._namespace

    def get(self, *args, **kwargs):
        if not hasattr(self, '_get'):
            raise NotImplementedError(
                '{} does not have {}'.format(self, '_get'))

        return self.resource_class(self, self._get(*args, **kwargs))

    def list(self, *args, **kwargs):
        if not hasattr(self, '_list'):
            raise NotImplementedError(
                '{} does not have {}'.format(self, '_list'))

        lst = self._list(*args, **kwargs)

        return [self.resource_class(self, item) for item in lst.items]

    def create(self, *args, **kwargs):
        if not hasattr(self, '_create'):
            raise NotImplementedError(
                '{} does not have {}'.format(self, '_create'))
        return self.resource_class(self, self._create(*args, **kwargs))

    def replace(self, *args, **kwargs):
        if not hasattr(self, '_replace'):
            raise NotImplementedError(
                '{} does not have {}'.format(self, '_replace'))
        return self._replace(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if not hasattr(self, '_delete'):
            raise NotImplementedError(
                '{} does not have {}'.format(self, '_delete'))
        return self._delete(*args, **kwargs)

    def deletecollection(self, *args, **kwargs):
        if not hasattr(self, '_deletecollection'):
            raise NotImplementedError(
                '{} does not have {}'.format(self, '_deletecollection'))
        return self._deletecollection(*args, **kwargs)
