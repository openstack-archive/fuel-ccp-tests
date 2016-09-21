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


import os
import time
import paramiko
import shutil
import tempfile
import traceback

import yaml

from fuel_ccp_tests import logger
from fuel_ccp_tests import settings

LOG = logger.logger


def get_test_method_name():
    raise NotImplementedError


def update_yaml(yaml_tree=None, yaml_value='', is_uniq=True,
                yaml_file=settings.TIMESTAT_PATH_YAML):
    """Store/update a variable in YAML file.

    yaml_tree - path to the variable in YAML file, will be created if absent,
    yaml_value - value of the variable, will be overwritten if exists,
    is_uniq - If false, add the unique two-digit suffix to the variable name.
    """
    if yaml_tree is None:
        yaml_tree = []
    yaml_data = {}
    if os.path.isfile(yaml_file):
        with open(yaml_file, 'r') as f:
            yaml_data = yaml.load(f)

    # Walk through the 'yaml_data' dict, find or create a tree using
    # sub-keys in order provided in 'yaml_tree' list
    item = yaml_data
    for n in yaml_tree[:-1]:
        if n not in item:
            item[n] = {}
        item = item[n]

    if is_uniq:
        last = yaml_tree[-1]
    else:
        # Create an uniq suffix in range '_00' to '_99'
        for n in range(100):
            last = str(yaml_tree[-1]) + '_' + str(n).zfill(2)
            if last not in item:
                break

    item[last] = yaml_value
    with open(yaml_file, 'w') as f:
        yaml.dump(yaml_data, f, default_flow_style=False)


class TimeStat(object):
    """Context manager for measuring the execution time of the code.

    Usage:
    with TimeStat([name],[is_uniq=True]):
    """

    def __init__(self, name=None, is_uniq=False):
        if name:
            self.name = name
        else:
            self.name = 'timestat'
        self.is_uniq = is_uniq
        self.begin_time = 0
        self.end_time = 0
        self.total_time = 0

    def __enter__(self):
        self.begin_time = time.time()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.end_time = time.time()
        self.total_time = self.end_time - self.begin_time

        # Create a path where the 'self.total_time' will be stored.
        yaml_path = []

        # There will be a list of one or two yaml subkeys:
        # - first key name is the method name of the test
        method_name = get_test_method_name()
        if method_name:
            yaml_path.append(method_name)

        # - second (subkey) name is provided from the decorator (the name of
        # the just executed function), or manually.
        yaml_path.append(self.name)

        try:
            update_yaml(yaml_path, '{:.2f}'.format(self.total_time),
                        self.is_uniq)
        except Exception:
            LOG.error("Error storing time statistic for {0}"
                      " {1}".format(yaml_path, traceback.format_exc()))
            raise

    @property
    def spent_time(self):
        return time.time() - self.begin_time


def reduce_occurrences(items, text):
    """ Return string without items(substrings)
        Args:
            items: iterable of strings
            test: string
        Returns:
            string
        Raise:
            AssertionError if any substing not present in source text
    """
    for item in items:
        LOG.debug(
            "Verifying string {} is shown in "
            "\"\"\"\n{}\n\"\"\"".format(item, text))
        assert text.count(item) != 0
        text = text.replace(item, "", 1)
    return text


def generate_keys():
    key = paramiko.RSAKey.generate(1024)
    public = key.get_base64()
    dirpath = tempfile.mkdtemp()
    key.write_private_key_file(os.path.join(dirpath, 'id_rsa'))
    with open(os.path.join(dirpath, 'id_rsa.pub'), 'w') as pub_file:
        pub_file.write(public)
    return dirpath


def clean_dir(dirpath):
    shutil.rmtree(dirpath)


def retry(tries_number=3, exception=Exception):
    def _retry(func):
        assert tries_number >= 1, 'ERROR! @retry is called with no tries!'

        def wrapper(*args, **kwargs):
            iter_number = 1
            while True:
                try:
                    LOG.debug('Calling function "{0}" with args "{1}" and '
                              'kwargs "{2}". Try # {3}.'.format(func.__name__,
                                                                args,
                                                                kwargs,
                                                                iter_number))
                    return func(*args, **kwargs)
                except exception as e:
                    if iter_number > tries_number:
                        LOG.debug('Failed to execute function "{0}" with {1} '
                                  'tries!'.format(func.__name__, tries_number))
                        raise e
                iter_number += 1
        return wrapper
    return _retry
