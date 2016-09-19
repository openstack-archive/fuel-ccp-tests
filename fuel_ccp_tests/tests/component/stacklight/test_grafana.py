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


@pytest.yield_fixture(scope='class')
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


@pytest.fixture(scope='class')
def system_dashboard(request, driver):
    """Login and return grafana system dashboard page"""
    login_page = grafana_pages.LoginPage(driver).open()
    main_page = login_page.login(username='admin', password='admin')
    return main_page.open_dashboard('system')


@pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
class TestGrafana(object):
    def check_percent_value(self, value, value_name):
        """Check that percent value is looks good"""
        value = value.strip()
        err_msg = "Expected that {} value {} ends with % sign".format(
            value_name, value)
        assert value.endswith('%'), err_msg
        value = value.strip('%')
        try:
            value = int(value)
        except ValueError:
            pytest.fail("Expected that {} value {} is integer",
                        format(value_name, value))
        err_msg = ('Expected that {} value {} is between 0 and 100 '
                   'and not equal 0').format(value_name, value)
        assert 0 < value <= 100, err_msg

    def check_decimal_values(self, value, value_name):
        """Checks that float values is looks good"""
        search_result = re.search(r'\d+(\.\d+)?', value)
        err_msg = "Expected that {} value {} contains decimal value".format(
            value_name, value)
        assert search_result is not None, err_msg
        value = search_result.group()
        try:
            value = float(value)
        except ValueError:
            pytest.fail("Expected that {} value {} is decimal",
                        format(value_name, value))

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
                self.check_percent_value(tooltip_values[key],
                                         value_name="CPU {}".format(key))

    def test_filesystem_metrics(self, system_dashboard):
        """Check filesystem metrics on Grafana system dashboard

        Scenario:
            * Login to Grafana
            * Go to system dashboard page
            * Select 1'st hostname
            * Select rootfs filesystem
            * Check free space value
            * Move mouse to disk usage graph
            * Check that "user", "reserved", "free" values are present
                on tooltip
            * Check free inodes value
            * Move mouse to inodes graph
            * Check that "user", "reserved", "free" values are present
                on tooltip
            * Repeat last 7 steps for each hostname
        """
        for host in system_dashboard.get_hostnames_list():
            system_dashboard.choose_hostname(host)
            system_dashboard.choose_filesystem('rootfs')

            # Check free space
            free_space = system_dashboard.get_fs_free_space()
            self.check_percent_value(free_space, value_name="free space")

            # Check disk usage
            disk_usage_panel = system_dashboard.get_disk_usage_panel()
            tooltip = system_dashboard.get_panel_tooltip(disk_usage_panel)
            tooltip_values = system_dashboard.get_tooltop_values(tooltip)
            for key in ("used", "reserved", "free"):
                err_msg = ("Grafana disk usage panel tooltip "
                           "doesn't contains {} value").format(key)
                assert key in tooltip_values, err_msg
                self.check_decimal_values(
                    tooltip_values[key],
                    value_name="disk usage {}".format(key))

            # Check free inodes
            free_inodes = system_dashboard.get_fs_free_inodes()
            self.check_percent_value(free_inodes, value_name="free space")

            # Check inodes
            inodes_panel = system_dashboard.get_inodes_panel()
            tooltip = system_dashboard.get_panel_tooltip(inodes_panel)
            tooltip_values = system_dashboard.get_tooltop_values(tooltip)
            for key in ("used", "reserved", "free"):
                err_msg = ("Grafana inodes panel tooltip "
                           "doesn't contains {} value").format(key)
                assert key in tooltip_values, err_msg
                self.check_decimal_values(tooltip_values[key],
                                          value_name="inodes {}".format(key))
