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

import contextlib
import functools
import time
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


def workload_fixture_generator(command):
    @pytest.yield_fixture
    def workload(admin_node):

        pids = set()

        def _make_workload():
            pid = admin_node.check_call('{} & echo $!'.format(
                command)).stdout_str
            # check process is running
            cmd = 'ls /proc/{}'.format(pid)
            err_msg = "Background process with pid `{}` is not found".format(
                pid)
            assert admin_node.execute(cmd).exit_code == 0, err_msg
            pids.add(pid)

        yield _make_workload

        for pid in pids:
            admin_node.execute('kill {}'.format(pid))

    return workload


cpu_workload = workload_fixture_generator(
    command='gzip < /dev/zero > /dev/null 2>&1')
dd_workload = workload_fixture_generator(
    command='dd if=/dev/zero of=/dev/null < /dev/null > /dev/null 2>&1')


@pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
class TestMetrics(object):
    def get_node_free_space(self, remote, mount_point='/'):
        return int(remote.check_call(
            "df | grep -E {}$ | awk '{{ print $4 }}'".format(
                mount_point)).stdout_str)

    def get_root_device(self, remote):
        return remote.check_call(
            "lsblk -l | grep -E '/$' | awk '{ print $1 }'").stdout_str

    def _get_cpu_metrics(self, remote):
        output = remote.check_call('cat /proc/stat | head -n1').stdout_str
        names = ('user', 'nice', 'system', 'idle', 'iowait', 'irq', 'softirq',
                 'steal', 'guest', 'guest_nice')
        values = map(int, output.split()[1:])
        return dict(zip(names, values))

    def _get_disk_metrics(self, remote, device):
        output = remote.check_call('cat /proc/diskstats | grep {}'.format(
            device)).stdout_str
        names = ('reads_ops', 'reads_merged', 'reads_sectors', 'reads_time',
                 'writes_ops', 'writes_merged', 'writes_sectors',
                 'writes_time', 'ios_in_progress', 'ios_in_progress_time',
                 'ios_in_progress_weighted_time')
        values = map(int, output.split()[3:])
        return dict(zip(names, values))

    @contextlib.contextmanager
    def _get_diff(self, get_values):
        """Call `get_values` on enter and exit and update result with diff

        Many linux kernel metrics (like /proc/stat, proc/diskstat) are
        cummulative. To retrieve changes of values we should read this file
        before and after some interval and calculate differences between
        values

        :param get_values: callable, which returns dict of ints of floats
        """
        result = {}
        old_values = get_values()
        yield result
        new_values = get_values()
        for x in new_values:
            result[x] = new_values[x] - old_values[x]

    @contextlib.contextmanager
    def node_cpu_stat(self, remote):
        """Collect values for /proc/stat during context manager
            executing"""
        get_values = functools.partial(self._get_cpu_metrics, remote)
        with self._get_diff(get_values) as values:
            yield values

    @contextlib.contextmanager
    def node_disk_stat(self, remote, device):
        """Collect values per seconds for /proc/diskstat during context manager
            executing"""
        get_values = functools.partial(self._get_disk_metrics,
                                       remote,
                                       device=device)
        start = time.time()
        result = {}
        with self._get_diff(get_values) as metrics:
            yield result
        duration = time.time() - start
        for k, v in metrics.items():
            result[k] = v / duration

    def get_node_loadavg(self, remote):
        return float(remote.check_call(
            "cat /proc/loadavg | awk '{ print $1 }'").stdout_str)

    def get_influxdb_measurements(self, influxdb, measure_regexp):
        """Returns list of measurements matched `measure_regexp`

        :param measure_regexp: string like '/intel\.procfs\.filesystem*/'
        """
        query = "SHOW MEASUREMENTS WITH MEASUREMENT =~ {}".format(
            measure_regexp)
        results = influxdb(query)
        return [x['name'] for y in results for x in y['measurements']]

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
        data = influxdb_actions.get_new_record(free_space_serie,
                                               conditions=query_conditions)
        # Get df free space from admin_node
        free = self.get_node_free_space(admin_node)
        assert free == pytest.approx(data['value'], rel=0.1)

        # Create file
        make_file(size_mb=100)

        data = influxdb_actions.get_new_record(free_space_serie,
                                               conditions=query_conditions)
        # Get df free space from admin_node
        free = self.get_node_free_space(admin_node)
        assert free == pytest.approx(data['value'], rel=0.1)

    def test_cpu_metrics(self, influxdb_actions, admin_node, cpu_workload):
        """Check reporting CPU metrics in InfluxDb

        Scenario:
            * Get measurements starts with `intel.procfs.cpu`
            * Get information from influxdb pod for all CPU series:
                    kubectl exec -it <pod name> -- influx -host <ip> \
                    -database ccp -execute "select count(value) \
                    from \"<series>\" where time > now() - 1d"
            * Check that all series contains some data
            * Check that cpu usage on influxdb nearly equal to
                `cat /proc/stat` result
            * Create small workload on node
            * Check that cpu usage on influxdb are increased
        """
        # Get series
        series = influxdb_actions.get_measurements('/intel\.procfs\.cpu*/')

        # Check series contains records
        for serie in series:
            influxdb_actions.check_serie_contains_records(serie)

        # Get admin_node CPU user_percentage
        user_percentage_serie = "intel.procfs.cpu.user_percentage"
        hostname = admin_node.check_call('hostname').stdout_str
        query_conditions = ("hostname='{hostname}' and cpuID='all'").format(
            hostname=hostname)

        # Compare last 5 metrics
        count = 5
        with self.node_cpu_stat(admin_node) as host_cpu_stat:
            influxdb_records = influxdb_actions.get_new_records(
                user_percentage_serie,
                conditions=query_conditions,
                count=count)
        # user_cpu is 1st value from metrics
        host_user_percentage = host_cpu_stat['user'] * 100.0 / sum(
            host_cpu_stat.values())
        influx_user_percentage = sum(x['value']
                                     for x in influxdb_records) / count
        assert host_user_percentage == pytest.approx(influx_user_percentage,
                                                     rel=0.5)

        # start workload
        cpu_workload()

        # Get influxdb and admin_node values again
        with self.node_cpu_stat(admin_node) as host_cpu_stat:
            influxdb_records = influxdb_actions.get_new_records(
                user_percentage_serie,
                conditions=query_conditions,
                count=count)
        # user_cpu is 1st value from metrics
        host_user_percentage = host_cpu_stat['user'] * 100.0 / sum(
            host_cpu_stat.values())
        influx_user_percentage = sum(x['value']
                                     for x in influxdb_records) / count
        assert host_user_percentage == pytest.approx(influx_user_percentage,
                                                     rel=0.5)

    def test_load_metrics(self, influxdb_actions, admin_node, dd_workload):
        """Check reporting load metrics in InfluxDb

        Scenario:
            * Get measurements starts with `intel.procfs.load`
            * Get information from influxdb pod for all filesystem series:
                    kubectl exec -it <pod name> -- influx -host <ip> \
                    -database ccp -execute "select count(value) \
                    from \"<series>\" where time > now() - 1d"
            * Check that all series contains some data
            * Check that load.mi1 value from influxdb nearly equal to
                `cat /proc/loadavg` output
            * Create some load on admin_node
            * Check that load.mi1 value from influxdb nearly equal to
                `cat /proc/loadavg` output again
        """
        # Get all load series
        series = influxdb_actions.get_measurements('/intel\.procfs\.load*/')

        # Check all series contains records
        for serie in series:
            influxdb_actions.check_serie_contains_records(serie)

        # Get admin_node load min1
        load_serie = "intel.procfs.load.min1"
        hostname = admin_node.check_call('hostname').stdout_str
        query_conditions = ("hostname='{hostname}'").format(hostname=hostname)
        data = influxdb_actions.get_new_record(load_serie,
                                               conditions=query_conditions)
        # Get /proc/loadavd 1st value from admin_node
        loadavg = self.get_node_loadavg(admin_node)
        assert loadavg == pytest.approx(data['value'], rel=0.5)

        # Make some load
        dd_workload()

        # Get influxdb and admin_node values again
        data = influxdb_actions.get_new_record(load_serie,
                                               conditions=query_conditions)
        loadavg = self.get_node_loadavg(admin_node)
        assert loadavg == pytest.approx(data['value'], rel=0.5)

    def test_disk_metrics(self, influxdb_actions, admin_node):
        """Check reporting disk metrics in InfluxDb

        Scenario:
            * Get measurements starts with `intel.procfs.disk`
            * Get information from influxdb pod for all filesystem series:
                    kubectl exec -it <pod name> -- influx -host <ip> \
                    -database ccp -execute "select count(value) \
                    from \"<series>\" where time > now() - 1d"
            * Check that all series contains some data
            * Check that intel.procfs.disk.ops_read value from influxdb
                nearly equal to `cat /proc/diskstats` output
            * Create some disk load on admin_node
            * Check that intel.procfs.disk.ops_read value from influxdb
                nearly equal to `cat /proc/diskstats` output
        """
        # Get all disk series
        series = influxdb_actions.get_measurements('/intel\.procfs\.disk*/')

        # Check all series contains records
        for serie in series:
            influxdb_actions.check_serie_contains_records(serie)

        # Get admin_node intel.procfs.disk.ops_read
        ops_read_serie = "intel.procfs.disk.ops_read"
        hostname = admin_node.check_call('hostname').stdout_str
        root_dev = self.get_root_device(admin_node)
        query_conditions = ("hostname='{hostname}' and disk='{disk}'").format(
            hostname=hostname, disk=root_dev)

        # Compare last `count` metrics from influxdb and host value
        count = 5
        with self.node_disk_stat(admin_node, root_dev) as host_disk_stat:
            influxdb_records = influxdb_actions.get_new_records(
                ops_read_serie,
                conditions=query_conditions,
                count=count)
        host_ops_read = host_disk_stat['reads_ops']
        influx_ops_read = sum(x['value'] for x in influxdb_records) / count
        assert host_ops_read == pytest.approx(influx_ops_read, abs=50, rel=0.4)

        # Make some load
        workload = workload_fixture_generator(
            'sudo dd if=/dev/{} of=/dev/null '
            '< /dev/null > /dev/null 2>&1'.format(root_dev))
        with contextlib.contextmanager(workload)(admin_node) as wl:
            wl()

            # Get influxdb and admin_node values again
            with self.node_disk_stat(admin_node, root_dev) as host_disk_stat:
                influxdb_records = influxdb_actions.get_new_records(
                    ops_read_serie,
                    conditions=query_conditions,
                    count=count)
            host_ops_read = host_disk_stat['reads_ops']
            influx_ops_read = sum(x['value'] for x in influxdb_records) / count
            assert host_ops_read == pytest.approx(
                influx_ops_read, abs=50, rel=0.4)
