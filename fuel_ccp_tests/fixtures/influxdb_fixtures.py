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

import functools

import pytest

from fuel_ccp_tests.managers import influxdb_manager


@pytest.fixture
def influxdb_actions(config, underlay, k8s_actions):
    remote_factory = functools.partial(underlay.remote,
                                       host=config.k8s.kube_host)
    k8sclient = k8s_actions.api
    ep = k8sclient.endpoints.get('influxdb', namespace='ccp')
    address = ep.subsets[0].addresses[0]
    pod_name = address.target_ref.name
    return influxdb_manager.InfluxDBManager(remote_factory, pod_name)
