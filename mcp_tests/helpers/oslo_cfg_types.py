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
import json
import os

from oslo_config import cfg
# See http://docs.openstack.org/developer/oslo.config/types.html
from oslo_config.types import Boolean, Integer, Float, String, MultiString,\
    List, Dict, IPAddress, Hostname, URI, ConfigType


# JSON config types inspired by https://review.openstack.org/100521
class JSONList(ConfigType):
    """JSON list type.

       Decode JSON list from a string value to python list.
    """

    def __init__(self, type_name='JSONList value'):
        super(JSONList, self).__init__(type_name=type_name)

    def __call__(self, value):
        if isinstance(value, list):
            return value

        try:
            result = json.loads(value)
        except ValueError:
            raise ValueError("No JSON object could be decoded from the value: "
                             "{0}".format(value))
        if not isinstance(result, list):
            raise ValueError("Expected JSONList, but decoded '{0}' from the "
                             "value: {1}".format(type(result), value))
        return result

    def __repr__(self):
        return 'JSONList'

    def __eq__(self, other):
        return self.__class__ == other.__class__

    def _formatter(self, value):
        return json.dumps(value)


class JSONDict(ConfigType):
    """JSON dictionary type.

       Decode JSON dictionary from a string value to python dict.
    """
    def __init__(self, type_name='JSONDict value'):
        super(JSONDict, self).__init__(type_name=type_name)

    def __call__(self, value):
        if isinstance(value, dict):
            return value

        try:
            result = json.loads(value)
        except ValueError:
            raise ValueError("No JSON object could be decoded from the value: "
                             "{0}".format(value))
        if not isinstance(result, dict):
            raise ValueError("Expected JSONDict, but decoded '{0}' from the "
                             "value: {1}".format(type(result), value))
        return result

    def __repr__(self):
        return 'JSONDict'

    def __eq__(self, other):
        return self.__class__ == other.__class__

    def _formatter(self, value):
        return json.dumps(value)


class Cfg(cfg.Opt):
    """Wrapper for cfg.Opt class that reads default form evironment variables.
    """
    def __init__(self, *args, **kwargs):
        super(Cfg, self).__init__(*args, **kwargs)
        env_var_name = self.name.upper()
        self.default = os.environ.get(env_var_name, self.default)
