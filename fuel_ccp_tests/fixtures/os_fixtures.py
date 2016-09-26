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

from time import sleep

import pytest

from fuel_ccp_tests import logger
from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests.managers.osmanager import OSManager

LOG = logger.logger


@pytest.fixture(scope='function')
def os_deployed(ccpcluster,
                hardware,
                underlay,
                revert_snapshot,
                config,
                k8s_actions):
    """Deploy openstack
    """
    # If no snapshot was reverted, then try to revert the snapshot
    # that belongs to the fixture.
    # Note: keep fixtures in strict dependences from each other!
    if not revert_snapshot:
        if hardware.has_snapshot(ext.SNAPSHOT.os_deployed) and \
                hardware.has_snapshot_config(ext.SNAPSHOT.os_deployed):
            hardware.revert_snapshot(ext.SNAPSHOT.os_deployed)

    osmanager = OSManager(config, underlay, k8s_actions, ccpcluster)
    if not config.os.running:
        LOG.info("Preparing openstack log collector fixture...")
        topology = None
        if config.os_deployed.stacklight:
            topology = ('/fuel_ccp_tests/templates/k8s_templates/'
                        'stacklight_topology.yaml')
        osmanager.install_os(topology=topology)
        hardware.create_snapshot(ext.SNAPSHOT.os_deployed)
    else:
        LOG.info("Openstack allready installed and running...")
        osmanager.check_os_ready()
