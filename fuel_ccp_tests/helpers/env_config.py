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

# TODO(slebedev): implement unit tests

import copy
import json
import re

from devops.helpers import templates
import yaml

from fuel_ccp_tests.helpers import exceptions
from fuel_ccp_tests import logger


LOG = logger.logger


class DevopsConfigMissingKey(KeyError):
    def __init__(self, key, keypath):
        super(DevopsConfigMissingKey, self).__init__()
        self.key = key
        self.keypath

    def __str__(self):
        return "Key '{0}' by keypath '{1}' is missing".format(
            self.key,
            self.keypath
        )


def fail_if_obj(x):
    if not isinstance(x, int):
        raise TypeError("Expecting int value!")


def fix_devops_config(config):
    """Function for get correct structure of config

    :param config: dict
    :returns: config dict
    """
    if not isinstance(config, dict):
        raise exceptions.DevopsConfigTypeError(
            type_name=type(config).__name__
        )
    if 'template' in config:
        return copy.deepcopy(config)
    else:
        return {
            "template": {
                "devops_settings": copy.deepcopy(config)
            }
        }


def list_update(obj, indexes, value):
    """Procedure for setting value into list (nested too), need
    in some functions where we are not able to set value directly.

    e.g.: we want to change element in nested list.

    obj = [12, 34, [3, 5, [0, 4], 3], 85]
    list_update(obj, [2, 2, 1], 50) => obj[2][2][1] = 50
    print(obj) => [12, 34, [3, 5, [0, 50], 3], 85]

    :param obj: source list
    :param indexes: list with indexes for recursive process
    :param value: some value for setting
    """
    def check_obj(obj):
        if not isinstance(obj, list):
            raise TypeError("obj must be a list instance!")
    check_obj(obj)
    if len(indexes) > 0:
        cur = obj
        last_index = indexes[-1]
        fail_if_obj(last_index)
        for i in indexes[:-1]:
            fail_if_obj(i)
            check_obj(cur[i])
            cur = cur[i]
        cur[last_index] = value


def return_obj(indexes=[]):
    """Function returns dict() or list() object given nesting, it needs by
    set_value_for_dict_by_keypath().

    Examples:
        return_obj() => {}
        return_obj([0]) => [{}]
        return_obj([-1]) => [{}]
        return_obj([-1, 1, -2]) => [[None, [{}, None]]]
        return_obj([2]) => [None, None, {}]
        return_obj([1,3]) => [None, [None, None, None, {}]]
    """
    if not isinstance(indexes, list):
        raise TypeError("indexes must be a list!")
    if len(indexes) > 0:
        # Create resulting initial object with 1 element
        result = [None]
        # And save it's ref
        cur = result
        # lambda for extending list elements
        li = (lambda x: [None] * x)
        # lambda for nesting of list
        nesting = (lambda x: x if x >= 0 else abs(x) - 1)
        # save last index
        last_index = indexes[-1]
        fail_if_obj(last_index)
        # loop from first till penultimate elements of indexes
        # we must create nesting list and set current position to
        # element at next index in indexes list
        for i in indexes[:-1]:
            fail_if_obj(i)
            cur.extend(li(nesting(i)))
            cur[i] = [None]
            cur = cur[i]
        # Perform last index
        cur.extend(li(nesting(last_index)))
        cur[last_index] = {}
        return result
    else:
        return dict()


def keypath(paths):
    """Function to make string keypath from list of paths"""
    return ".".join(list(paths))


def disassemble_path(path):
    """Func for disassembling path into key and indexes list (if needed)

    :param path: string
    :returns: key string, indexes list
    """
    pattern = re.compile("\[([0-9]*)\]")
    # find all indexes of possible list object in path
    indexes = (lambda x: [int(r) for r in pattern.findall(x)]
               if pattern.search(x) else [])
    # get key
    base_key = (lambda x: re.sub(pattern, '', x))
    return base_key(path), indexes(path)


def set_value_for_dict_by_keypath(source, paths, value, new_on_missing=True):
    """Procedure for setting specific value by keypath in dict

    :param source: dict
    :param paths: string
    :param value: value to set by keypath
    """
    paths = paths.lstrip(".").split(".")
    walked_paths = []
    # Store the last path
    last_path = paths.pop()
    data = source
    # loop to go through dict
    while len(paths) > 0:
        path = paths.pop(0)
        key, indexes = disassemble_path(path)
        walked_paths.append(key)
        if key not in data:
            if new_on_missing:
                # if object is missing, we create new one
                data[key] = return_obj(indexes)
            else:
                raise DevopsConfigMissingKey(key, keypath(walked_paths[:-1]))

        data = data[key]

        # if we can not get element in list, we should
        # throw an exception with walked path
        for i in indexes:
            try:
                tmp = data[i]
            except IndexError as err:
                LOG.error(
                    "Couldn't access {0} element of '{1}' keypath".format(
                        i, keypath(walked_paths)
                    )
                )
                LOG.error(
                    "Dump of '{0}':\n{1}".format(
                        keypath(walked_paths),
                        json.dumps(data)
                    )
                )
                raise type(err)(
                    "Can't access '{0}' element of '{1}' object! "
                    "'{2}' object found!".format(
                        i,
                        keypath(walked_paths),
                        data
                    )
                )
            data = tmp
            walked_paths[-1] += "[{0}]".format(i)

    key, indexes = disassemble_path(last_path)
    i_count = len(indexes)
    if key not in data:
        if new_on_missing:
            data[key] = return_obj(indexes)
        else:
            raise DevopsConfigMissingKey(key, keypath(walked_paths))
    elif i_count > 0 and not isinstance(data[key], list):
        raise TypeError(
            ("Key '{0}' by '{1}' keypath expected as list "
             "but '{3}' obj found").format(
                 key, keypath(walked_paths), type(data[key]).__name__
            )
        )
    if i_count == 0:
        data[key] = value
    else:
        try:
            list_update(data[key], indexes, value)
        except (IndexError, TypeError) as err:
            LOG.error(
                "Error while setting by '{0}' key of '{1}' keypath".format(
                    last_path,
                    keypath(walked_paths)
                )
            )
            LOG.error(
                "Dump of object by '{0}' keypath:\n{1}".format(
                    keypath(walked_paths),
                    json.dumps(data)
                )
            )
            raise type(err)(
                "Couldn't set value by '{0}' key of '{1}' keypath'".format(
                    last_path,
                    keypath(walked_paths)
                )
            )


class EnvironmentConfig(object):
    def __init__(self):
        super(EnvironmentConfig, self).__init__()
        self._config = None

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config):
        """Setter for config

        :param config: dict
        """
        self._config = fix_devops_config(config)

    def __getitem__(self, key):
        if self._config is not None:
            conf = self._config['template']['devops_settings']
            return copy.deepcopy(conf.get(key, None))
        else:
            return None

    @logger.logwrap
    def set_value_by_keypath(self, keypath, value):
        """Function for set value of devops settings by keypath.

        It's forbidden to set value of self.config directly, so
        it's possible simply set value by keypath
        """
        if self.config is None:
            raise exceptions.DevopsConfigIsNone()
        conf = self._config['template']['devops_settings']
        set_value_for_dict_by_keypath(conf, keypath, value)

    def save(self, filename):
        """Dump current config into given file

        :param filename: string
        """
        if self._config is None:
            raise exceptions.DevopsConfigIsNone()
        with open(filename, 'w') as f:
            f.write(
                yaml.dump(
                    self._config, default_flow_style=False
                )
            )

    def load_template(self, filename):
        """Method for reading file with devops config

        :param filename: string
        """
        if filename is not None:
            LOG.debug(
                "Preparing to load config from template '{0}'".format(
                    filename
                )
            )
            self.config = templates.yaml_template_load(filename)
        else:
            LOG.error("Template filename is not set, loading config " +
                      "from template aborted.")
