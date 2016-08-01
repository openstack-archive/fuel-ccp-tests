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

from mcp_tests import settings


@pytest.fixture(scope='function')
def cluster_roles():
    """Store initial cluster roles

    :return: dict deploy_images_conf
    """
    deploy_images_conf = {
        'kubectl_label_nodes': {
            'openstack-compute-controller': [
                'node1',
                'node2',
                'node3',
            ],
            'openstack-controller': [
                'node1',
            ],
            'openstack-compute': [
                'node2',
                'node3',
            ]
        },
        'registry': settings.REGISTRY,
        'images_namespace': settings.IMAGES_NAMESPACE,
        'images_tag': settings.IMAGES_TAG
    }
    return deploy_images_conf
