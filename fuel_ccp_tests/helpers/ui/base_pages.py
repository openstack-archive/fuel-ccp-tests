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

import selenium.common.exceptions as Exceptions
from selenium import webdriver
from selenium.webdriver.remote import webelement
import selenium.webdriver.support.ui as Support
from selenium.webdriver.support import expected_conditions
from six.moves.urllib import parse

from fuel_ccp_tests.helpers.ui import ui_settings


class ImproperlyConfigured(Exception):
    """Raises on some errors in pages classes configuration"""
    pass


class BaseWebObject(object):
    def __init__(self, driver, timeout=5):
        self.driver = driver
        self.timeout = timeout

    def _turn_off_implicit_wait(self):
        self.driver.implicitly_wait(0)

    def _turn_on_implicit_wait(self):
        self.driver.implicitly_wait(self.timeout)

    @contextlib.contextmanager
    def waits_disabled(self):
        try:
            self._turn_off_implicit_wait()
            yield
        finally:
            self._turn_on_implicit_wait()

    def _is_element_present(self, *locator):
        with self.waits_disabled():
            try:
                self._get_element(*locator)
                return True
            except Exceptions.NoSuchElementException:
                return False

    def _is_element_visible(self, *locator):
        try:
            return self._get_element(*locator).is_displayed()
        except (Exceptions.NoSuchElementException,
                Exceptions.ElementNotVisibleException):
            return False

    def _is_element_displayed(self, element):
        if element is None:
            return False
        try:
            if isinstance(element, webelement.WebElement):
                return element.is_displayed()
            else:
                return element.src_elem.is_displayed()
        except (Exceptions.ElementNotVisibleException,
                Exceptions.StaleElementReferenceException):
            return False

    def _is_text_visible(self, element, text, strict=True):
        if not hasattr(element, 'text'):
            return False
        if strict:
            return element.text == text
        else:
            return text in element.text

    def _get_element(self, *locator):
        return self.driver.find_element(*locator)

    def _get_elements(self, *locator):
        return self.driver.find_elements(*locator)

    def _fill_field_element(self, data, field_element):
        field_element.clear()
        field_element.send_keys(data)
        return field_element

    def _select_dropdown(self, value, element):
        select = Support.Select(element)
        select.select_by_visible_text(value)

    def _select_dropdown_by_value(self, value, element):
        select = Support.Select(element)
        select.select_by_value(value)

    def _get_dropdown_options(self, element):
        select = Support.Select(element)
        return select.options

    def get_action(self):
        return webdriver.ActionChains(self.driver)

    def get_wait(self, timeout=ui_settings.explicit_wait):
        return Support.WebDriverWait(self.driver, timeout)


class PageObject(BaseWebObject):
    """Base class for page objects."""

    URL = None

    def __init__(self, driver):
        """Constructor."""
        super(PageObject, self).__init__(driver)
        self._page_title = None

    @property
    def page_title(self):
        return self.driver.title

    def open(self):
        if self.URL is None:
            raise ImproperlyConfigured('`open` method requires {!r} has '
                                       'not None URL class variable')
        url = parse.urljoin(self.get_current_page_url(), self.URL)
        self.driver.get(url)
        return self

    @contextlib.contextmanager
    def wait_for_page_load(self, timeout=10):
        old_page = self.driver.find_element_by_tag_name('html')
        yield
        self.get_wait(timeout).until(expected_conditions.staleness_of(
            old_page))

    def is_the_current_page(self, do_assert=False):
        self.get_wait().until(expected_conditions.title_contains(
            self._page_title))
        found_expected_title = self.page_title.startswith(self._page_title)
        if do_assert:
            err_msg = ("Expected to find %s in page title, instead found: %s" %
                       (self._page_title, self.page_title))
            assert found_expected_title, err_msg
        return found_expected_title

    def get_current_page_url(self):
        return self.driver.current_url

    def close_window(self):
        return self.driver.close()

    def is_nth_window_opened(self, n):
        return len(self.driver.window_handles) == n

    def switch_window(self, name=None, index=None):
        """Switches focus between the webdriver windows.
        Args:
        - name: The name of the window to switch to.
        - index: The index of the window handle to switch to.
        If the method is called without arguments it switches to the
         last window in the driver window_handles list.
        In case only one window exists nothing effectively happens.
        Usage:
        page.switch_window(name='_new')
        page.switch_window(index=2)
        page.switch_window()
        """

        if name is not None and index is not None:
            raise ValueError("switch_window receives the window's name or "
                             "the window's index, not both.")
        if name is not None:
            self.driver.switch_to.window(name)
        elif index is not None:
            self.driver.switch_to.window(self.driver.window_handles[index])
        else:
            self.driver.switch_to.window(self.driver.window_handles[-1])

    def go_to_previous_page(self):
        self.driver.back()

    def go_to_next_page(self):
        self.driver.forward()

    def refresh_page(self):
        self.driver.refresh()
