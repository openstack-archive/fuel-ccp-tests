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

import uuid

import pytest
from influxdb import InfluxDBClient
from devops.helpers import helpers

from fuel_ccp_tests.logger import logger


@pytest.yield_fixture(scope='function')
def admin_node(config, underlay):
    """Return <remote> object to k8s admin node"""
    logger.info("Get SSH access to admin node")
    with underlay.remote(host=config.k8s.kube_host) as remote:
        yield remote


@pytest.fixture
def external_ip(config):
    return config.k8s.kube_host


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
    def get_influxdb_client(self,
                            k8sclient,
                            external_ip,
                            login='root',
                            password='root',
                            db='ccp'):
        service = k8sclient.services.get(name='influxdb', namespace='ccp')
        return InfluxDBClient(external_ip, service.spec.ports[0].node_port,
                              login, password, db)

    def get_node_free_space(self, remote, dev='vda'):
        return int(remote.check_call(
            "df | grep /dev/{} | awk '{{ print $4 }}'".format(dev)).stdout_str)

    def get_influxdb_last_record(self,
                                 dbclient,
                                 serie,
                                 conditions=None,
                                 updated_after=0):
        conditions = " and {}".format(conditions) if conditions else ""
        if isinstance(updated_after, int):
            updated_after = '{}s'.format(updated_after)
        else:
            updated_after = "'{}'".format(updated_after)
        query = ("select * from \"{serie}\" "
                 "where time > {updated_after} {conditions} "
                 "order by time desc limit 1").format(
                     serie=serie,
                     conditions=conditions,
                     updated_after=updated_after)

        data = []

        def _get_data():
            result = dbclient.query(query)
            try:
                data.append(next(result.get_points()))
                return True
            except StopIteration:
                return False

        helpers.wait(
            _get_data,
            timeout=60 * 5,
            timeout_msg="Timeout waiting data for query `{}`".format(query))
        return data[-1]

    def test_filesystem_metrics(self, make_file, k8s_actions, admin_node,
                                external_ip):
        """Check reporting filesystem metrics in InfluxDb

        Scenario:
            * Get information from influxdb pod for next series:
                    kubectl exec -it <pod name> -- influx -host <ip> \
                    -database ccp -execute "select * from \"<series>\" \
                    where time > now() - 1d"

                where series is:
                    intel.procfs.filesystem.inodes_free
                    intel.procfs.filesystem.inodes_reserved
                    intel.procfs.filesystem.inodes_used
                    intel.procfs.filesystem.space_free
                    intel.procfs.filesystem.space_reserved
                    intel.procfs.filesystem.space_used
                    intel.procfs.filesystem.inodes_percent_free
                    intel.procfs.filesystem.inodes_percent_reserved
                    intel.procfs.filesystem.inodes_percent_used
                    intel.procfs.filesystem.space_percent_free
                    intel.procfs.filesystem.space_percent_reserved
                    intel.procfs.filesystem.space_percent_used
                    intel.procfs.filesystem.device_name
                    intel.procfs.filesystem.device_type
            * Check that all series returns some data
            * Check that free space from ifluxdb nearly equal to df output
            * Create 100M file on node
            * Check that free spase on ifluxdb are decrease
        """
        free_space_serie = "intel.procfs.filesystem.space_free"
        series = (free_space_serie, "intel.procfs.filesystem.inodes_free",
                  "intel.procfs.filesystem.inodes_reserved",
                  "intel.procfs.filesystem.inodes_used",
                  "intel.procfs.filesystem.space_reserved",
                  "intel.procfs.filesystem.space_used",
                  "intel.procfs.filesystem.inodes_percent_free",
                  "intel.procfs.filesystem.inodes_percent_reserved",
                  "intel.procfs.filesystem.inodes_percent_used",
                  "intel.procfs.filesystem.space_percent_free",
                  "intel.procfs.filesystem.space_percent_reserved",
                  "intel.procfs.filesystem.space_percent_used",
                  "intel.procfs.filesystem.device_name",
                  "intel.procfs.filesystem.device_type")
        k8sclient = k8s_actions.api
        dbclient = self.get_influxdb_client(k8sclient, external_ip=external_ip)
        for serie in series:
            query = 'select * from "{}" where time > now() - 1d'.format(serie)
            err_msg = "There is no results for query `{}` in influxdb".format(
                query)
            results = dbclient.query(query)
            assert len(list(results.get_points())) > 0, err_msg

        hostname = admin_node.check_call('hostname').stdout_str

        query_conditions = ("hostname='{hostname}' and "
                            "filesystem='rootfs'").format(hostname=hostname)

        data = self.get_influxdb_last_record(dbclient,
                                             free_space_serie,
                                             conditions=query_conditions)
        free = self.get_node_free_space(admin_node)
        assert free == pytest.approx(data['value'], rel=1e-2)

        # Create file
        make_file(size_mb=100)

        # Retrive data twice for avoiding old record retriving
        for _ in range(2):
            data = self.get_influxdb_last_record(dbclient,
                                                 free_space_serie,
                                                 conditions=query_conditions,
                                                 updated_after=data['time'])
        free = self.get_node_free_space(admin_node)
        assert free == pytest.approx(data['value'], rel=1e-2)
