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

from mcp_tests.helpers import mcp_tests_exceptions as exc


class EnvironmentManagerEmpty(object):
    """Class-helper for creating VMs via devops environments"""

    def __init__(self, config=None):
        """Initializing class instance and create the environment

        :param config: oslo.config object
        :param config.hardware.conf_path: path to devops YAML template
        :param config.hardware.current_snapshot: name of the snapshot that
                                                 descriebe environment status.
        """
        self.__config = config

    def get_ssh_data(self)
        raise Exception("EnvironmentManagerEmpty doesn't have SSH details. "
                        "Please provide SSH details in config.underlay.ssh")

    def create_snapshot(self, name, description=None):
        self.__config.hardware.current_snapshot = name

    def revert_snapshot(self, name):
        if self.__config.hardware.current_snapshot != name:
            raise Exception(
                "EnvironmentManagerEmpty cannot revert nodes from {} to {}"
                .format(self.__config.hardware.current_snapshot, name))

    def resume(self):
        """Resume environment"""
        pass

    def suspend(self):
        """Suspend environment"""
        pass

    def stop(self):
        """Stop environment"""
        pass

    def has_snapshot(self, name):
        return self.__config.hardware.current_snapshot == name

    def delete_environment(self):
        """Delete environment"""
        pass
