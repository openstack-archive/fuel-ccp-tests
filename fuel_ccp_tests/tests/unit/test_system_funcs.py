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

import pytest

from fuel_ccp_tests.helpers import post_install_k8s_checks as funcs

test_images1 = [
    "artifactory.example.net:5000/hyperkube-amd64:v1.4.1-test_100",
    "andyshinn/dnsmasq:2.72",
    "artifactory.example.net:5001/calico/node:v0.20.0-mcp-7b31adc",
    "artifactory.example.net:5001/calico/ctl:v0.20.0-mcp-7b31adc",
    "artifactory.example.net:5000/hyperkube-amd64:v1.4.1-test_100",
]

test_images2 = [
    "andyshinn/dnsmasq:2.72",
    "gcr.io/google_containers/pause-amd64:3.0",
    "quay.io/coreos/etcd:v3.0.1",
]

required_images = [
    "andyshinn/dnsmasq",
    "calico/node",
    "hyperkube-amd64",
]


class MockUnderlay(object):
    def __init__(self, images):
        self.images = images

    def sudo_check_call(self, *args, **kwargs):
        return {'stdout': self.images}


@pytest.mark.unit_tests
def test_required_images_exists():
    funcs.required_images_exists(node_name='master',
                                 underlay=MockUnderlay(test_images1),
                                 required_images=required_images)
    with pytest.raises(AssertionError):
        funcs.required_images_exists(node_name='master',
                                     underlay=MockUnderlay(test_images2),
                                     required_images=required_images)
