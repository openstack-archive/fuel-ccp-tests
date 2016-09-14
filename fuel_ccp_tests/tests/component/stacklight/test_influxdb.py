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
import uuid

import pytest
from devops.helpers import helpers

from fuel_ccp_tests import logger

LOG = logger.logger


@pytest.yield_fixture(scope='function')
def admin_node(config, underlay):
    """Return <remote> object to k8s admin node"""
    with underlay.remote(host=config.k8s.kube_host) as remote:
        yield remote


@pytest.fixture
def influxdb(k8s_actions, admin_node):
    """Return callable wich performs query to influxdb and return result"""
    k8sclient = k8s_actions.api
    ep = k8sclient.endpoints.get('influxdb', namespace='ccp')
    address = ep.subsets[0].addresses[0]

    def _make_query(query):
        cmd = ('kubectl exec -it {pod_name} -- '
               'influx -host {bind_ip} -database ccp -execute "{query}" '
               '-format json'.format(pod_name=address.target_ref.name,
                                     bind_ip=address.ip,
                                     query=query.replace('"', '\\"')))
        LOG.info("Performing {} on admin_node".format(cmd))
        response = admin_node.check_call(
            'kubectl exec -it {pod_name} -- '
            'influx -host {bind_ip} -database ccp -execute "{query}" '
            '-format json'.format(pod_name=address.target_ref.name,
                                  bind_ip=address.ip,
                                  query=query.replace('"', '\\"')))
        data = json.loads(response.stdout_str)

        # Transform response
        result = []
        for group in data['results']:
            if len(group) > 0:
                for serie in group['series']:
                    records = [dict(zip(serie['columns'], x))
                               for x in serie['values']]
                    result.append({serie['name']: records})
        return result

    return _make_query


@pytest.yield_fixture
def make_file(admin_node):

    files = set()

    def _make_file(size_mb):
        filename = uuid.uuid4()
        files.add(filename)
        admin_node.check_call('dd if=/dev/zero of=/tmp/{0} '
                              'bs=1M count={1}'.format(filename, size_mb))

    yield _make_file
    for filename in files:
        admin_node.execute('rm /tmp/{}'.format(filename))


class TestMetrics(object):
    def get_node_free_space(self, remote, mount_point='/'):
        return int(remote.check_call(
            "df | grep -E {}$ | awk '{{ print $4 }}'".format(
                mount_point)).stdout_str)

    def get_influxdb_measurements(self, influxdb, measure_regexp):
        """Returns list of measurements matched `measure_regexp`

        :param measure_regexp: string like '/intel\.procfs\.filesystem*/'
        """
        query = "SHOW MEASUREMENTS WITH MEASUREMENT =~ {}".format(
            measure_regexp)
        results = influxdb(query)
        return [x['name'] for y in results for x in y['measurements']]

    def check_influxdb_serie_contains_records(self,
                                              influxdb,
                                              serie,
                                              duration='1d'):
        """Checks that influxdb contains records with last `duration` interval

        :param serie: name of the serie to check
        :param duration: string with relative offset back from now
        """
        query = ('select count(value) from "{}" '
                 'where time > now() - {}').format(serie, duration)
        results = influxdb(query)
        count = results[0][serie][0]['count']
        err_msg = ("There is no records for serie `{}` "
                   "in influxdb for last `{}`").format(serie, duration)
        assert count > 0, err_msg

    def get_influxdb_last_record(self,
                                 influxdb,
                                 serie,
                                 conditions=None,
                                 updated_after=0):
        conditions = " and {}".format(conditions) if conditions else ""
        query = ("select * from \"{serie}\" "
                 "where time > {updated_after} {conditions} "
                 "order by time desc limit 1").format(
                     serie=serie,
                     conditions=conditions,
                     updated_after=updated_after)

        data = []

        def _get_data():
            result = influxdb(query)
            try:
                data.append(result[0][serie][0])
                return True
            except IndexError:
                return False

        helpers.wait(
            _get_data,
            timeout=60 * 2,
            timeout_msg="Timeout waiting data for query `{}`".format(query))
        return data[-1]

    def test_filesystem_metrics(self, make_file, influxdb, admin_node):
        """Check reporting filesystem metrics in InfluxDb

        Scenario:
            * Get measurements starts with `intel.procfs.filesystem`
            * Get information from influxdb pod for all filesystem series:
                    kubectl exec -it <pod name> -- influx -host <ip> \
                    -database ccp -execute "select count(value) \
                    from \"<series>\" where time > now() - 1d"
            * Check that all series contains some data
            * Check that free space from influxdb nearly equal to df output
            * Create 100M file on node
            * Check that free spase on influxdb are decrease
        """
        # Get all filesystem series
        series = self.get_influxdb_measurements(influxdb,
                                                '/intel\.procfs\.filesystem*/')

        # Check series contains records
        for serie in series:
            self.check_influxdb_serie_contains_records(influxdb, serie)

        # Get admin_node free space
        free_space_serie = "intel.procfs.filesystem.space_free"
        hostname = admin_node.check_call('hostname').stdout_str
        query_conditions = ("hostname='{hostname}' and "
                            "filesystem='rootfs'").format(hostname=hostname)
        data = self.get_influxdb_last_record(influxdb,
                                             free_space_serie,
                                             conditions=query_conditions)
        # Get df free space from admin_node
        free = self.get_node_free_space(admin_node)
        assert free == pytest.approx(data['value'], rel=0.1)

        # Create file
        make_file(size_mb=100)

        # Retrive data twice for avoiding old record retriving
        for _ in range(2):
            data = self.get_influxdb_last_record(influxdb,
                                                 free_space_serie,
                                                 conditions=query_conditions,
                                                 updated_after=data['time'])
        # Get df free space from admin_node
        free = self.get_node_free_space(admin_node)
        assert free == pytest.approx(data['value'], rel=0.1)
