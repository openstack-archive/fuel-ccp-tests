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

from devops.helpers.helpers import tcp_ping
from devops.helpers.helpers import wait

from mcp_tests import settings
from mcp_tests.helpers.containers import exec_in_container
from mcp_tests.logger import logger
from mcp_tests.service_tests import ServiceBaseTest


@pytest.mark.skipif(settings.PRIVATE_REGISTRY is None,
                    reason="PRIVATE_REGISTRY isn't set")
class TestMysqlImage(ServiceBaseTest):
    """Test class consits simple tests for mysql container"""

    services = [
        {
            "name": "mariadb",
            "image": "{}/nextgen/mariadb".format(settings.PRIVATE_REGISTRY),
            "environment": {
                "DB_ROOT_PASSWORD": "r00tme"
            },
            "ports": ["33306:3306"]
        }
    ]
    wait_services = 30

    @pytest.mark.mysql_base
    def test_mysql_check_mysqld(self):
        """Start container from image, check if mysql is running

        Scenario:
            4. Check access from root user

        """
        logger.info("Trying check daemon")
        container = self.containers[0]
        cmd = 'pgrep mysqld'
        out, exit_code = exec_in_container(container, cmd)
        assert exit_code == 0

    @pytest.mark.mysql_base
    def test_mysql_is_running(self):
        """Start container from image, check if mysql is running

        Scenario:
            3. Check port 3306

        """
        logger.info("Trying to reach port 3306")
        wait(lambda: tcp_ping('localhost', 33306),
             timeout=30,
             timeout_msg="MySQL port in not reacheble.")

    @pytest.mark.mysql_base
    def test_mysql_is_accessible(self):
        """Start container from image, check if mysql is running

        Scenario:
            4. Check access from root user

        """
        logger.info("Trying fetch databases list")
        container = self.containers[0]
        cmd = 'mysql -Ns -uroot -pr00tme -e "SHOW DATABASES"'
        out, exit_code = exec_in_container(container, cmd)
        assert exit_code == 0

        out = filter(bool, out.split('\n'))
        logger.info("Databases in DB - {}".format(out))
        assert set(out) == \
            set(['information_schema', 'mysql', 'performance_schema'])
