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

from mcp_tests.helpers import env_config


class Manager(object):
    """Base manager class."""

    def __init__(self):
        super(Manager, self).__init__()
        self.__devops_config = env_config.EnvironmentConfig()
        self._start_time = 0
        self._env = None

    @property
    def devops_config(self):
        return self.__devops_config

    @devops_config.setter
    def devops_config(self, conf):
        """Setter for self.__devops_config

        :param conf: mcp_tests.helpers.env_config.EnvironmentConfig
        """
        if not isinstance(conf, env_config.EnvironmentConfig):
            msg = ("Unexpected type of devops config. Got '{0}' " +
                   "instead of '{1}'")
            raise TypeError(
                msg.format(
                    type(conf).__name__,
                    env_config.EnvironmentConfig.__name__
                )
            )
        self.__devops_config = conf
