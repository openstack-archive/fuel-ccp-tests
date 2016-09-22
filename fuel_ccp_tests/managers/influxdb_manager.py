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

from devops.helpers import helpers

from fuel_ccp_tests import logger

LOG = logger.logger


class InfluxDBManager(object):
    def __init__(self, remote_factory, pod_name):
        self.remote_factory = remote_factory
        self.pod_name = pod_name

    def _make_query(self, query, verbose=True):
        cmd = ('kubectl exec -it {0.pod_name} -- '
               'influx -host {0.pod_name} -database ccp -execute "{1}" '
               '-format json'.format(self, query.replace('"', '\\"')))
        if verbose:
            LOG.info("Performing `{}` on admin_node".format(cmd))
        with self.remote_factory() as remote:
            response = remote.check_call(cmd)
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

    def get_measurements(self, measure_regexp):
        """Returns list of measurements matched `measure_regexp`

        :param measure_regexp: string like '/intel\.procfs\.filesystem*/'
        """
        query = "SHOW MEASUREMENTS WITH MEASUREMENT =~ {}".format(
            measure_regexp)
        results = self._make_query(query)
        return [x['name'] for y in results for x in y['measurements']]

    def check_serie_contains_records(self, serie, duration='1d'):
        """Checks that influxdb contains records with last `duration` interval

        :param serie: name of the serie to check
        :param duration: string with relative offset back from now
        """
        query = ('select count(value) from "{}" '
                 'where time > now() - {}').format(serie, duration)
        results = self._make_query(query)
        count = results[0][serie][0]['count']
        err_msg = ("There is no records for serie `{}` "
                   "in influxdb for last `{}`").format(serie, duration)
        assert count > 0, err_msg

    def get_last_record(self,
                        serie,
                        conditions=None,
                        updated_after=0,
                        timeout=2 * 60):
        conditions = " and {}".format(conditions) if conditions else ""
        query = ("select * from \"{serie}\" "
                 "where time > {updated_after} {conditions} "
                 "order by time desc limit 1").format(
                     serie=serie,
                     conditions=conditions,
                     updated_after=updated_after)

        data = []

        def _get_data():
            result = self._make_query(query, verbose=_get_data.verbose)
            _get_data.verbose = False
            try:
                data.append(result[0][serie][0])
                return True
            except IndexError:
                return False

        _get_data.verbose = True
        helpers.wait(
            _get_data,
            timeout=timeout,
            interval=1,
            timeout_msg="Timeout waiting data for query `{}`".format(query))
        return data[-1]

    def get_new_records(self, serie, count, conditions=None, timeout=2 * 60):
        """Return `count` new record (what will appear in future) from db"""
        record = self.get_last_record(serie, conditions)
        records = []
        for n in range(count):
            record = self.get_last_record(serie,
                                          conditions,
                                          updated_after=record['time'],
                                          timeout=timeout)
            records.append(record)
        return records

    def get_new_record(self, serie, conditions=None, timeout=2 * 60):
        """Return first new record (what will appear in future) from db"""
        return self.get_new_records(serie=serie,
                                    count=1,
                                    conditions=conditions,
                                    timeout=timeout)[0]
