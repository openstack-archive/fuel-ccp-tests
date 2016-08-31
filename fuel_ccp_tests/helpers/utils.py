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

from devops.helpers import helpers
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from elasticsearch import Elasticsearch

from fuel_ccp_tests.helpers import ext

LOG = logger.logger


def get_test_method_name():
    raise NotImplementedError


def update_yaml(yaml_tree=None, yaml_value='', is_uniq=True,
                yaml_file=settings.TIMESTAT_PATH_YAML, remote=None):
    """Store/update a variable in YAML file.

    yaml_tree - path to the variable in YAML file, will be created if absent,
    yaml_value - value of the variable, will be overwritten if exists,
    is_uniq - If false, add the unique two-digit suffix to the variable name.
    """
    def get_file(path, remote=None, mode="r"):
        if remote:
            return remote.open(path, mode)
        else:
            return open(path, mode)

    if yaml_tree is None:
        yaml_tree = []
    with get_file(yaml_file, remote) as file_obj:
        yaml_data = yaml.safe_load(file_obj)

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
    with get_file(yaml_file, remote, mode='w') as file_obj:
        yaml.dump(yaml_data, file_obj, default_flow_style=False)


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

class ElasticClient(object):
    def __init__(self, host='localhost', port=9200):
        self.es = Elasticsearch([{'host': '{}'.format(host),
                                  'port': port}])
        self.host = host
        self.port = port

    def find(self, key, value):
        LOG.info('Search for {} for {}'.format(key, value))
        search_request_body = '{' +\
            '  "query": {' +\
            '   "simple_query_string": {' +\
            '     "query": "{}",'.format(value) +\
            '     "analyze_wildcard" : "true",' +\
            '     "fields" : ["{}"],'.format(key) +\
            '     "default_operator": "AND"' +\
            '     }' +\
            ' },' +\
            '  "size": 1' +\
            '}'
        LOG.info('Search by {}'.format(search_request_body))

        def is_found():
            def temporary_status():
                res = self.es.search(index='_all', body=search_request_body)
                return res['hits']['total'] != 0
            return temporary_status

        predicate = is_found()
        helpers.wait(predicate, timeout=300,
                     timeout_msg='Timeout waiting, result from elastic')

        es_raw = self.es.search(index='_all', body=search_request_body)
        if es_raw['timed_out']:
            raise RuntimeError('Elastic search timeout exception')

        return ElasticSearchResult(key, value, es_raw['hits']['total'], es_raw)


class ElasticSearchResult(object):
    def __init__(self, key, value, count, raw):
        self.key = key
        self.value = value
        self.count = count
        self.raw = raw
        if self.count != 0:
            self.items = raw['hits']['hits']

    def get(self, index):
        if self.count != 0:
            return self.items[index]['_source']
        else:
            None


def create_file(node, pod, path, size,
                namespace=ext.Namespace.BASE_NAMESPACE):
    node.check_call(
        'kubectl exec {} --namespace={} {}'.format(
            pod.name,
            namespace,
            'dd -- if=/dev/zero -- of={} bs=1MB count={}'.format(path, size)),
        expected=[ext.ExitCodes.EX_OK])


def run_daily_cron(node, pod, task,
                   namespace=ext.Namespace.BASE_NAMESPACE):
    node.check_call(
        'kubectl exec {} --namespace={} {}'.format(
            pod.name,
            namespace,
            '/etc/cron.daily/{}'.format(task)),
        expected=[ext.ExitCodes.EX_OK])


def list_files(node, pod, path, mask,
               namespace=ext.Namespace.BASE_NAMESPACE):
    return "".join(node.check_call(
        'kubectl exec {} --namespace={} {}'.format(
            pod.name,
            namespace,
            'find {} -- -iname {}'.format(path, mask)),
        expected=[ext.ExitCodes.EX_OK])['stdout']) \
        .replace('\n', ' ').strip().split(" ")


def rm_files(node, pod, path,
             namespace=ext.Namespace.BASE_NAMESPACE):
    node.execute(
        'kubectl exec {} --namespace={} {}'.format(
            pod.name,
            namespace,
            'rm -- {}'.format(path)))
