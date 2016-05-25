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
import logging
import time

import docker
from compose.project import Project
from compose.service import Service

from mcp_tests.logger import logger
from mcp_tests.logger import console

logging.getLogger('compose.service').addHandler(console)


class ServiceBaseTest(object):
    """ServiceBaseTest contains setup/teardown for services up and down"""

    @classmethod
    def setup_class(cls):
        """Start container from image

        Scenario:
            1. Get image from private registry
            2. Start container with it
        """
        logger.info("Up services")
        cli = docker.Client()
        project_name = cls.__name__
        services = []
        for s in cls.services:
            services.append(
                Service(
                    # name=s['name'],
                    project=project_name,
                    client=cli,
                    **s))
        cls.project = Project(
            name=project_name,
            services=services,
            client=cli)
        cls.containers = cls.project.up()
        wait_services = getattr(cls, 'wait_services', 5)
        logger.info("Sleep {} sec until MariDB is setting up".format(
            wait_services))
        time.sleep(wait_services)
        logger.info("Start tests")

    @classmethod
    def teardown_class(cls):
        """Down service

        Scenario:
            5. Kill container
            6. Remove volumes

        """
        logger.info("Down service and remove volume")
        cls.project.down(remove_image_type=False,
                         include_volumes=True)
