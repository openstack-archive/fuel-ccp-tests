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

from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests import logger

LOG = logger.logger


@pytest.yield_fixture
def admin_node(config, underlay):
    """Return <remote> object to k8s admin node"""
    with underlay.remote(host=config.k8s.kube_host) as remote:
        yield remote


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


@pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
class TestMetrics(object):
    def get_node_free_space(self, remote, mount_point='/'):
        return int(remote.check_call(
            "df | grep -E {}$ | awk '{{ print $4 }}'".format(
                mount_point)).stdout_str)

    def test_filesystem_metrics(self, make_file, influxdb_actions, admin_node):
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
        series = influxdb_actions.get_measurements(
            '/intel\.procfs\.filesystem*/')

        # Check series contains records
        for serie in series:
            influxdb_actions.check_serie_contains_records(serie)

        # Get admin_node free space
        free_space_serie = "intel.procfs.filesystem.space_free"
        hostname = admin_node.check_call('hostname').stdout_str
        query_conditions = ("hostname='{hostname}' and "
                            "filesystem='rootfs'").format(hostname=hostname)
        data = influxdb_actions.get_last_record(free_space_serie,
                                                conditions=query_conditions)
        # Get df free space from admin_node
        free = self.get_node_free_space(admin_node)
        assert free == pytest.approx(data['value'], rel=0.1)

        # Create file
        make_file(size_mb=100)

        # Retrive data twice for avoiding old record retriving
        for _ in range(2):
            data = influxdb_actions.get_last_record(
                free_space_serie,
                conditions=query_conditions,
                updated_after=data['time'])
        # Get df free space from admin_node
        free = self.get_node_free_space(admin_node)
        assert free == pytest.approx(data['value'], rel=0.1)
