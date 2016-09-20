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
import re

import pytest

from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests.helpers.ui import ui_tester
from fuel_ccp_tests.helpers.ui import grafana_pages


@pytest.yield_fixture
def driver(request):
    url = os.environ.get('GRAFANA_URL')
    if url is None:
        underlay = request.getfixturevalue('underlay')
        nodes = underlay.node_names()
        ip = underlay.host_by_node_name(nodes[0])
        k8s_actions = request.getfixturevalue('k8s_actions')
        k8sclient = k8s_actions.api
        service = k8sclient.services.get('grafana', namespace='ccp')
        port = service.spec.ports[0].node_port
        url = "http://{}:{}/".format(ip, port)
    with ui_tester.ui_driver(url) as driver:
        yield driver


@pytest.fixture
def system_dashboard(request, driver):
    """Login and return grafana system dashboard page"""
    login_page = grafana_pages.LoginPage(driver).open()
    main_page = login_page.login(username='admin', password='admin')
    return main_page.open_dashboard('system')


@pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
class TestGrafana(object):
    def test_cpu_metrics(self, system_dashboard):
        """Check CPU metrics on Grafana system dashboard

        Scenario:
            * Login to Grafana
            * Go to system dashboard page
            * Select 1'st hostname
            * Move mouse to CPU graph
            * Check that "user", "system", "idle" values are present on tooltip
            * Repeat last 3 steps for each hostname
        """
        for host in system_dashboard.get_hostnames_list():
            system_dashboard.choose_hostname(host)
            cpu_panel = system_dashboard.get_cpu_panel()
            tooltip = system_dashboard.get_panel_tooltip(cpu_panel)
            tooltip_values = system_dashboard.get_tooltop_values(tooltip)
            for key in ("user", "system", "idle"):
                err_msg = ("Grafana CPU panel tooltip "
                           "doesn't contains {} value").format(key)
                assert key in tooltip_values, err_msg
                err_msg = ("Grafana CPU panel tooltip value for {} "
                           "is 0% or has wrong format").format(key)
                assert re.search(r'[1-9][0-9]*?%',
                                 tooltip_values[key]) is not None, err_msg
