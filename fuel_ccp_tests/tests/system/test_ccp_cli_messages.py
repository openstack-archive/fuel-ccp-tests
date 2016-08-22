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

from fuel_ccp_tests.logger import logger
from fuel_ccp_tests.helpers.utils import StringHelper


class CliMessages(object):
    error_message = "ccp show-dep: error: too few arguments"
    usage_message = "usage: ccp [-h] "
    usage_show_dep_message = \
        "usage: ccp show-dep [-h] components [components ...]"
    help_message = [
        "positional arguments:",
        "components  CCP components to show dependencies",
        "optional arguments:",
        "-h, --help  show this help message and exit"]
    error_message_bad_component_name = "Wrong component name '{}'"
    error_message_unrecognized_arguments = \
        "ccp: error: unrecognized arguments: {}"


@pytest.yield_fixture(scope='module')
def admin_node(config, underlay, ccpcluster):
    logger.info("Get SSH access to admin node")
    with underlay.remote(host=config.k8s.kube_host) as remote:
        yield remote


class TestCppCliNormalMessageInShowDep(object):
    """Check info messages when show-dep is success"""

    @pytest.mark.fail_snapshot
    def test_component_have_single_dependency(self, admin_node):
        logger.info("Show info for component with single dependency")
        component = ["memcached"]
        dependencies = ["etcd"]
        cmd = "ccp show-dep {}".format(component[0])
        result = admin_node.check_call(cmd, expected=[0])
        result_no_fetch = filter(
            lambda s: "fuel_ccp.fetch" not in s, result['stdout'])
        result_normalized = \
            " ".join(result_no_fetch).replace("\n", " ").strip().split(' ')
        assert set(dependencies) == set(result_normalized)

    @pytest.mark.fail_snapshot
    def test_component_have_multiple_dependencies(self, admin_node):
        logger.info("Show info for component with multiple dependencies")
        component = ["keystone"]
        dependencies = ["mariadb", "etcd"]
        cmd = "ccp show-dep {}".format(component[0])
        result = admin_node.check_call(cmd, expected=[0])
        result_no_fetch = filter(
            lambda s: "fuel_ccp.fetch" not in s, result['stdout'])
        result_normalized = \
            " ".join(result_no_fetch).replace("\n", " ").strip().split(' ')
        assert set(dependencies) == set(result_normalized)

    @pytest.mark.fail_snapshot
    def test_component_have_no_dependencies(self, admin_node):
        logger.info("Show info for component without dependencies")
        no_dependencies_message = "expected message"
        component = ["etcd"]
        dependencies = [""]
        cmd = "ccp show-dep {}".format(component[0])
        result = admin_node.check_call(cmd, expected=[0])
        result_no_fetch = filter(
            lambda s: "fuel_ccp.fetch" not in s, result['stdout'])
        result_normalized = \
            " ".join(result_no_fetch).replace("\n", " ").strip().split(' ')
        assert set(dependencies) == set(result_normalized)

    @pytest.mark.fail_snapshot
    def test_component_help_message_via_short(self, admin_node):
        logger.info("Show help message with short option")
        cmd = "ccp show-dep -h"
        result = admin_node.check_call(cmd, expected=[0])
        assert len(StringHelper.reduce_occurrences(
            [CliMessages.usage_show_dep_message] + CliMessages.help_message,
            " ".join(result['stdout'])).strip()) == 0

    @pytest.mark.fail_snapshot
    def test_component_help_message_via_long(self, admin_node):
        logger.info("Show help message with long option")
        cmd = "ccp show-dep --help"
        result = admin_node.check_call(cmd, expected=[0])
        assert len(StringHelper.reduce_occurrences(
            [CliMessages.usage_show_dep_message] + CliMessages.help_message,
            " ".join(result['stdout'])).strip()) == 0

    @pytest.mark.fail_snapshot
    def test_multiple_components_given(self, admin_node):
        logger.info(
            "Show info for several components"
            " with dependencies no cross-referenced")
        component = ["keystone", "memcached"]
        dependencies = ["mariadb", "etcd"]
        cmd = "ccp show-dep {}".format(" ".join(component))
        result = admin_node.check_call(cmd, expected=[0])
        result_no_fetch = filter(
            lambda s: "fuel_ccp.fetch" not in s, result['stdout'])
        result_normalized = \
            " ".join(result_no_fetch).replace("\n", " ").strip().split(' ')
        assert set(dependencies) == set(result_normalized)

    @pytest.mark.fail_snapshot
    def test_multiple_components_given_cross_reference(self, admin_node):
        logger.info(
            "Show info for component with multiple dependencies with"
            "cross referenced dependecies")
        component = ["keystone", "etcd"]
        dependencies = ["mariadb"]
        cmd = "ccp show-dep {}".format(" ".join(component))
        result = admin_node.check_call(cmd, expected=[0])
        result_no_fetch = filter(
            lambda s: "fuel_ccp.fetch" not in s, result['stdout'])
        result_normalized = \
            " ".join(result_no_fetch).replace("\n", " ").strip().split(' ')
        assert set(dependencies) == set(result_normalized)


class TestCppCliErrorMessageInShowDep(object):
    """Check error messages when show-dep is failing"""

    @pytest.mark.fail_snapshot
    def test_nonexistent_component_given(self, admin_node):
        logger.info("Show error message for nonexistent component name")
        component = ["wrong_component"]
        expected = 1
        error_message = CliMessages.error_message_bad_component_name.format(
            component[0])
        cmd = "ccp show-dep {}".format(component[0])
        result = admin_node.check_call(cmd, expected=[expected])
        assert error_message in " ".join(result['stderr'])

    @pytest.mark.fail_snapshot
    def test_no_components_given(self, admin_node):
        logger.info("Show error message for no component")
        cmd = "ccp show-dep"
        expected = 2
        result = admin_node.check_call(cmd, expected=[expected])
        assert len(
            StringHelper.reduce_occurrences(
                [CliMessages.error_message,
                 CliMessages.usage_show_dep_message],
                "".join(
                    result['stderr'])).strip()) == 0
        assert len(
            " ".join(result['stdout']).strip()) == 0


class TestCppCliErrorMessage(object):
    """Check error messages for unexpected options"""

    @pytest.mark.fail_snapshot
    def test_unexpected_option_given(self, admin_node):
        argrument = "--unrecognized-long"
        cmd = "ccp show-dep {} any_componenet".format(argrument)
        expected = 2
        result = admin_node.check_call(cmd, expected=[expected])
        assert len(StringHelper.reduce_occurrences(
            [CliMessages.usage_message,
             CliMessages.error_message_unrecognized_arguments.format(
                 argrument)] + CliMessages.options_list,
            " ".join(result['stderr']).strip())) == 0
