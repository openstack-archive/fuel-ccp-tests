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

from selenium.webdriver.common import by
from selenium.webdriver.support import expected_conditions as EC
from selenium.common import exceptions as selenium_exception

from fuel_ccp_tests.helpers.ui import base_pages


class LoginPage(base_pages.PageObject):

    _login_username_field_locator = (by.By.NAME, 'username')
    _login_password_field_locator = (by.By.NAME, 'password')
    _login_submit_button_locator = (by.By.CLASS_NAME, "btn")

    URL = '/login'

    def __init__(self, driver):
        super(LoginPage, self).__init__(driver)
        self._page_title = "Grafana"

    @property
    def username_field(self):
        return self._get_element(*self._login_username_field_locator)

    @property
    def password_field(self):
        return self._get_element(*self._login_password_field_locator)

    @property
    def login_button(self):
        return self._get_element(*self._login_submit_button_locator)

    def login(self, username, password):
        self.open()
        self._fill_field_element(username, self.username_field)
        self._fill_field_element(password, self.password_field)
        with self.wait_for_page_load():
            self.login_button.click()

        page = MainPage(self.driver)
        page.is_the_current_page(do_assert=True)
        return page


class DashboardPage(base_pages.PageObject):
    _submenu_controls_locator = (by.By.CLASS_NAME, "submenu-controls")
    _submenu_item_xpath_tpl = (
        './/*[contains(@class, "submenu-item")]'
        '[.//*[text()="{}"]]'
        '//*[contains(@class, "variable-link-wrapper")]')
    _hostname_selector = (by.By.XPATH,
                          _submenu_item_xpath_tpl.format('Hostname:'))
    _disk_selector = (by.By.XPATH, _submenu_item_xpath_tpl.format('Disks:'))
    _interface_selector = (by.By.XPATH,
                           _submenu_item_xpath_tpl.format('Interface:'))
    _filesystem_selector = (by.By.XPATH,
                            _submenu_item_xpath_tpl.format('Filesystem:'))
    _variable_option_selector = (by.By.CLASS_NAME, 'variable-option')

    _panel_selector = (by.By.TAG_NAME, 'grafana-panel')
    _panel_title_text_selector = (by.By.CLASS_NAME, 'panel-title-text')

    _tooltip_selector = (by.By.ID, 'tooltip')

    _tooltip_series_name_selector = (by.By.CLASS_NAME,
                                     'graph-tooltip-series-name')
    _tooltip_series_value_selector = (by.By.CLASS_NAME, 'graph-tooltip-value')

    _singlestat_panel_value_selector = (by.By.CLASS_NAME,
                                        'singlestat-panel-value')

    _loading_selector = (by.By.CLASS_NAME, 'panel-loading')

    def __init__(self, driver, dashboard_name):
        super(DashboardPage, self).__init__(driver)
        self._page_title = "Grafana - {}".format(dashboard_name)

    def _wait_load(self):
        self.get_wait().until(EC.invisibility_of_element_located(
            self._loading_selector))

    def is_dashboards_page(self):
        return (self.is_the_current_page() and
                self._is_element_visible(*self._submenu_controls_locator))

    def get_back_to_home(self):
        self.go_to_previous_page()

        page = MainPage(self.driver)
        page.is_the_current_page(do_assert=True)
        return page

    @property
    def submenu(self):
        return self._get_element(*self._submenu_controls_locator)

    def _get_submenu_list(self, selector):
        submenu_item_list = self.submenu.find_element(*selector)
        submenu_item_list.click()
        return submenu_item_list.find_elements(*self._variable_option_selector)

    def _get_submenu_items_names(self, selector):
        return [x.text for x in self._get_submenu_list(selector)]

    def _choose_submenu_item_value(self, selector, value):
        list_items = self._get_submenu_list(selector)
        mapping = {x.text.lower(): x for x in list_items}
        if 'selected' in mapping[value].get_attribute('class').split():
            mapping[value].click()
        mapping[value].click()
        self._wait_load()

    def get_hostnames_list(self):
        return self._get_submenu_items_names(self._hostname_selector)

    def choose_hostname(self, value):
        return self._choose_submenu_item_value(self._hostname_selector, value)

    def get_disks_list(self):
        return self._get_submenu_items_names(self._disk_selector)

    def choose_disk(self, value):
        return self._choose_submenu_item_value(self._disk_selector, value)

    def get_interfaces_list(self):
        return self._get_submenu_items_names(self._interface_selector)

    def choose_interface(self, value):
        return self._choose_submenu_item_value(self._interface_selector, value)

    def get_filesystems_list(self):
        return self._get_submenu_items_names(self._filesystem_selector)

    def choose_filesystem(self, value):
        return self._choose_submenu_item_value(self._filesystem_selector,
                                               value)

    def _get_panels_mapping(self):
        panels = self._get_elements(*self._panel_selector)
        return {x.find_element(*self._panel_title_text_selector).text: x
                for x in panels}

    def get_cpu_panel(self):
        return self._get_panels_mapping()['CPU']

    def get_disk_usage_panel(self):
        return next(v for k, v in self._get_panels_mapping().items()
                    if k.startswith('Disk usage'))

    def get_inodes_panel(self):
        return next(v for k, v in self._get_panels_mapping().items()
                    if k.startswith('inodes'))

    def get_load_panel(self):
        return self._get_panels_mapping()['System load']

    def get_fs_free_space(self):
        panel = self._get_panels_mapping()['Free space']
        return panel.find_element(*self._singlestat_panel_value_selector).text

    def get_fs_free_inodes(self):
        panel = self._get_panels_mapping()['Free inodes']
        return panel.find_element(*self._singlestat_panel_value_selector).text

    def get_panel_tooltip(self, panel):
        size = panel.size
        action = self.get_action()
        action.move_to_element_with_offset(panel, size['width'] / 2,
                                           size['height'] / 2)
        action.perform()
        return self._get_element(*self._tooltip_selector)

    def get_tooltop_values(self, tooltip):
        result = {}
        series_names = tooltip.find_elements(
            *self._tooltip_series_name_selector)
        series_values = tooltip.find_elements(
            *self._tooltip_series_value_selector)
        for series_name, series_value in zip(series_names, series_values):
            result[series_name.text.strip(':')] = series_value.text
        return result


class MainPage(base_pages.PageObject):
    _dropdown_menu_locator = (by.By.LINK_TEXT, 'Home')

    _dashboards_list_locator = (by.By.CLASS_NAME, 'search-results-container')

    _dashboard_locator = (by.By.CLASS_NAME, 'search-result-link')

    def __init__(self, driver):
        super(MainPage, self).__init__(driver)
        self._page_title = "Grafana - Home"

    def is_main_page(self):
        return (self.is_the_current_page() and
                self._is_element_visible(*self._dropdown_menu_locator))

    @property
    def dropdown_menu(self):
        return self._get_element(*self._dropdown_menu_locator)

    @property
    def dashboards_list(self):
        self.open_dropdown_menu()
        return self._get_element(*self._dashboards_list_locator)

    @property
    def dashboards(self):
        return self.dashboards_list.find_elements(*self._dashboard_locator)

    def is_dropdown_menu_opened(self):
        return self._is_element_present(*self._dashboards_list_locator)

    def open_dropdown_menu(self):
        if not self.is_dropdown_menu_opened():
            self.dropdown_menu.click()

    def open_dashboard(self, dashboard_name):
        dashboards_mapping = {dashboard.text.lower(): dashboard
                              for dashboard in self.dashboards}
        dashboards_mapping[dashboard_name.lower()].click()
        dashboard_page = DashboardPage(self.driver, dashboard_name)
        dashboard_page.is_dashboards_page()
        return dashboard_page
