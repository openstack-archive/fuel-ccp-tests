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
import json
import uuid
import pytest

from time import sleep
from fuel_ccp_tests.helpers import utils
from fuel_ccp_tests.logger import logger
from fuel_ccp_tests.helpers import ext


@pytest.yield_fixture(scope='function')
def admin_node(config, underlay, ccpcluster):
    logger.info("Get SSH access to admin node")
    with underlay.remote(host=config.k8s.kube_host) as remote:
        yield remote


@pytest.yield_fixture(scope='function')
def elastic_client_public(os_deployed_stacklight, admin_node, config):
    elastic_search_public_port = ''.join(admin_node.execute(
        "kubectl get service --namespace ccp elasticsearch -o yaml |"
        " awk '/nodePort: / {print $NF}'")['stdout'][0].strip())

    elastic_search_public_host = config.k8s.kube_host

    yield utils.ElasticClient(elastic_search_public_host,
                              elastic_search_public_port)


@pytest.yield_fixture(scope='function')
def elastic_client_private(os_deployed_stacklight, admin_node, config):
    elastic_search_service_host = \
        ''.join(
            admin_node.execute(
                "kubectl get pods "
                "--selector=app=elasticsearch "
                "--namespace=ccp -o wide "
                "| awk 'FNR==2{print $6}'"
            )['stdout']).strip()

    elastic_search_service_port = ''.join(admin_node.execute(
        "kubectl get service --namespace ccp elasticsearch -o yaml |"
        " awk '/port: / {print $NF}'")['stdout'][0].strip())

    yield utils.ElasticClient(elastic_search_service_host,
                              elastic_search_service_port)


@pytest.fixture(scope='function')
def kibana_public_endpoint(os_deployed_stacklight, admin_node, config):
    kibana_public_port = ''.join(admin_node.execute(
        "kubectl get service --namespace ccp kibana -o yaml |"
        " awk '/nodePort: / {print $NF}'")['stdout'][0].strip())

    kibana_public_address = config.k8s.kube_host

    return '{}:{}'.format(kibana_public_address, kibana_public_port)


@pytest.mark.ccp_logging
# @pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
@pytest.mark.revert_snapshot(ext.SNAPSHOT.os_deployed_stacklight)
class TestCppLogging(object):
    """Check logging aggregation"""
    def test_logging_connection_to_elasticsearch_public(
            self, admin_node, elastic_client_public):
        """Elasticsearch api test
                Scenario:
                1. Install k8s
                2. Install microservices
                3. Fetch all repos
                4. Build images or use external registry
                5. Deploy openstack
                6. Test elasticsearch is accessibile on public ip
        """
        logger.info("Test connection to elasticsearch via public endpoint")

        elastic_call = 'curl -s -o /dev/null -w "%{{http_code}}" http://{}:{}/'
        elastic_http_response = admin_node.execute(elastic_call.format(
            elastic_client_public.host,
            elastic_client_public.port))['stdout']

        assert ext.HttpCodes.OK in elastic_http_response, \
            "Elastic respond with unexpected " \
            "HTTP_RESPONSE on public endpoint Expected {} Actual {}".format(
                ext.HttpCodes.OK, elastic_http_response)
        return

    def test_logging_connection_to_elasticsearch_private(
            self,
            admin_node,
            elastic_client_private):
        """Elasticsearch api test
                Scenario:
                1. Install k8s
                2. Install microservices
                3. Fetch all repos
                4. Build images or use external registry
                5. Deploy openstack
                6. Test elasticsearch is accessibile on private ip
        """
        logger.info(
            'Test connection to elasticsearch service via private endpoint')
        elastic_call = 'curl -s -o /dev/null -w "%{{http_code}}" http://{}:{}/'
        elastic_http_response = admin_node.execute(
            elastic_call.format(
                elastic_client_private.host,
                elastic_client_private.port))['stdout']
        assert ext.HttpCodes.OK in elastic_http_response, \
            "Elastic respond with unexpected " \
            "HTTP_RESPONSE on private endpoint Expected {} Actual {}".format(
                ext.HttpCodes.OK, elastic_http_response)
        return

    def test_logging_search_for_logs_from_all_running_heka_instances(
            self, admin_node, k8scluster, elastic_client_public):
        """Heka connection test
                Scenario:
                1. Install k8s
                2. Install microservices
                3. Fetch all repos
                4. Build images or use external registry
                5. Deploy openstack
                6. Find logs from all heka nodes
                6. Test that logs from each heka node exist
        """

        logger.info('Search for logs from all heka instances')
        ec = elastic_client_public
        k8sclient = k8scluster.api
        # get all nodes
        nodes = k8sclient.nodes.list()
        # get all heka instances
        hekas = filter(lambda x: 'heka' in x.name,
                       k8sclient.pods.list(
                           namespace=ext.Namespace.BASE_NAMESPACE))
        # ensure heka is running on each node
        assert len(nodes) == len(hekas)

        for heka_job in hekas:
            logger.info('Checking presense in aggregated log messages from {}'
                        .format(heka_job.name))
            assert ec.find('Hostname', heka_job.name).count > 0, \
                "Log message from heka node {} not found on elastic".format(
                    heka_job
                )

    def test_logging_trigger_event_into_mysql(self,
                                              admin_node,
                                              k8scluster,
                                              elastic_client_public):
        """Trigger event in mysql container
                Scenario:
                1. Install k8s
                2. Install microservices
                3. Fetch all repos
                4. Build images or use external registry
                5. Deploy openstack
                6. Get mysql pod
                7. Trigger mysql log event inside the container
                8. Test that triggered event pushed to elasticsearch
        """
        ec = elastic_client_public
        k8sclient = k8scluster.api

        mysql_pod = \
            filter(lambda x: 'mariadb' in x.name, k8sclient.pods.list(
                namespace=ext.Namespace.BASE_NAMESPACE))[0]

        mysql_id = str(uuid.uuid4()).replace('-', '')
        mysql_template = \
            '2016-08-31 16:02:05 139704672115456 [Note] {}\n'.format(mysql_id)

        admin_node.check_call(
            'kubectl exec {} --namespace={} {}'.format(
                mysql_pod.name,
                ext.Namespace.BASE_NAMESPACE,
                'sed -- -i -- \'$ a\{}\' /var/log/ccp/mysql/mysql.log'.format(
                    mysql_template)
            ),
            expected=[ext.ExitCodes.EX_OK])
        sleep(10)

        injected = ec.find('Payload', mysql_id)
        assert injected.count == 1, \
            "New log message from mysql from {} not picked by heka".format(
                mysql_pod)

    def test_logging_trigger_event_into_rabitmq(self,
                                                admin_node,
                                                k8scluster,
                                                elastic_client_public):
        """Trigger event in rabbitmq container
                Scenario:
                1. Install k8s
                2. Install microservices
                3. Fetch all repos
                4. Build images or use external registry
                5. Deploy openstack
                6. Get rabbitmq pod
                7. Trigger rabbitmq log event inside the container
                8. Test that triggered event pushed to elasticsearch
        """
        ec = elastic_client_public

        k8sclient = k8scluster.api

        rabbitmq_pod = \
            filter(lambda x: 'rabbitmq' in x.name, k8sclient.pods.list(
                namespace=ext.Namespace.BASE_NAMESPACE))[0]

        rabbitmq_id = str(uuid.uuid4()).replace('-', '')
        rabbitmq_template = \
            ["=INFO REPORT==== 31-Aug-2016::15:55:55 ===",
             "{}".format(rabbitmq_id)]

        admin_node.check_call(
            'kubectl exec {} --namespace={} {}'.format(
                rabbitmq_pod.name,
                ext.Namespace.BASE_NAMESPACE,
                'sed -- -i -- \'$ a\{}\' /var/log/ccp/rabbitmq/rabbitmq.log'
                .format(rabbitmq_template[0])),
            expected=[ext.ExitCodes.EX_OK])
        admin_node.check_call(
            'kubectl exec {} --namespace={} {}'.format(
                rabbitmq_pod.name,
                ext.Namespace.BASE_NAMESPACE,
                'sed -- -i -- \'$ a\{}\' /var/log/ccp/rabbitmq/rabbitmq.log'
                .format(rabbitmq_template[1])),
            expected=[ext.ExitCodes.EX_OK])
        sleep(10)

        injected = ec.find('Payload', rabbitmq_id)
        assert injected.count == 1,\
            "New log message from mysql from {} not picked by heka".format(
                rabbitmq_pod)

    def test_logging_attributes_for_mysql_message(self,
                                                  elastic_client_public):
        """Test attibute population consistency for mysql
                Scenario:
                1. Install k8s
                2. Install microservices
                3. Fetch all repos
                4. Build images or use external registry
                5. Deploy openstack
                6. Search mysql log event in the elasticsearch
                7. Test logged message consistency
        """
        ec = elastic_client_public
        event = ec.find('Logger', 'mysql').get(0)
        self.check_message_format(event, 'mysql')

    def test_logging_attributes_for_rabbitmq_message(
            self,
            elastic_client_public):
        """Test attibute population consistency for rabbitmq
                Scenario:
                1. Install k8s
                2. Install microservices
                3. Fetch all repos
                4. Build images or use external registry
                5. Deploy openstack
                6. Search rabbitmq log event in the elasticsearch
                7. Test logged message consistency
        """
        ec = elastic_client_public
        event = ec.find('Logger', 'rabbitmq').get(0)
        self.check_message_format(event, 'rabbitmq')

    def test_logging_attributes_for_openstack_horizon_apache_message(
            self,
            elastic_client_public):
        """Test attibute population consistency for horizon-apache
                Scenario:
                1. Install k8s
                2. Install microservices
                3. Fetch all repos
                4. Build images or use external registry
                5. Deploy openstack
                6. Search horizon-apache log event in the elasticsearch
                7. Test logged message consistency
        """
        ec = elastic_client_public
        event = ec.find('Logger', 'openstack.horizon-apache').get(0)
        self.check_message_format(event, 'openstack.horizon-apache')

    def test_logging_attributes_for_openstack_keystone_message(
            self,
            elastic_client_public):
        """Test attibute population consistency for keystone
                Scenario:
                1. Install k8s
                2. Install microservices
                3. Fetch all repos
                4. Build images or use external registry
                5. Deploy openstack
                6. Search keystone log event in the elasticsearch
                7. Test logged message consistency
        """
        ec = elastic_client_public
        event = ec.find('Logger', 'openstack.keystone').get(0)
        self.check_message_format(event, 'openstack.keystone')

    def test_logging_attributes_for_openstack_keystone_apache_message(
            self,
            elastic_client_public):
        """Test attibute population consistency for keystone-apache
                Scenario:
                1. Install k8s
                2. Install microservices
                3. Fetch all repos
                4. Build images or use external registry
                5. Deploy openstack
                6. Search keystone-apache log event in the elasticsearch
                7. Test logged message consistency
        """
        ec = elastic_client_public
        event = ec.find('Logger', 'openstack.keystone-apache').get(0)
        self.check_message_format(event, 'openstack.keystone-apache')

    def test_logging_attributes_for_openstack_nova_message(
            self,
            elastic_client_public):
        """Test attibute population consistency for nova
                Scenario:
                1. Install k8s
                2. Install microservices
                3. Fetch all repos
                4. Build images or use external registry
                5. Deploy openstack
                6. Search nova log event in the elasticsearch
                7. Test logged message consistency
        """
        ec = elastic_client_public
        event = ec.find('Logger', 'openstack.nova').get(0)
        self.check_message_format(event, 'openstack.nova')

    def test_logging_attributes_for_openstack_neutron_message(
            self,
            elastic_client_public):
        """Test attibute population consistency for neutron
                Scenario:
                1. Install k8s
                2. Install microservices
                3. Fetch all repos
                4. Build images or use external registry
                5. Deploy openstack
                6. Search neutron log event in the elasticsearch
                7. Test logged message consistency
        """
        ec = elastic_client_public
        event = ec.find('Logger', 'openstack.neutron').get(0)
        self.check_message_format(event, 'openstack.neutron')

    def test_logging_attributes_for_openstack_glance_message(
            self,
            elastic_client_public):
        """Test attibute population consistency for glance
                Scenario:
                1. Install k8s
                2. Install microservices
                3. Fetch all repos
                4. Build images or use external registry
                5. Deploy openstack
                6. Search glance log event in the elasticsearch
                7. Test logged message consistency
        """
        ec = elastic_client_public
        event = ec.find('Logger', 'openstack.glance').get(0)
        self.check_message_format(event, 'openstack.glance')

    def test_logging_attributes_for_openstack_heat_message(
            self, deploy_openstack_stacklight,
            elastic_client_public):
        """Test attibute population consistency for heat
                Scenario:
                1. Install k8s
                2. Install microservices
                3. Fetch all repos
                4. Build images or use external registry
                5. Deploy openstack
                6. Search heat log event in the elasticsearch
                7. Test logged message consistency
        """
        ec = elastic_client_public
        event = ec.find('Logger', 'openstack.heat').get(0)
        self.check_message_format(event, 'openstack.heat')

    def test_logging_attributes_for_openvswitch_message(
            self,
            elastic_client_public):
        """Test attibute population consistency for openvswitch
                Scenario:
                1. Install k8s
                2. Install microservices
                3. Fetch all repos
                4. Build images or use external registry
                5. Deploy openstack
                6. Search openvswitch log event in the elasticsearch
                7. Test logged message consistency
        """
        ec = elastic_client_public
        event = ec.find('Logger', 'openvswitch').get(0)
        self.check_message_format(event, 'openvswitch')

    def test_logging_explore_indexes_with_kibana(
            self,
            admin_node,
            kibana_public_endpoint):
        """Test index availability from kibana
                Scenario:
                1. Install k8s
                2. Install microservices
                3. Fetch all repos
                4. Build images or use external registry
                5. Deploy openstack
                6. Get kibana service status
                7. Test overal status should be green
        """
        status_full = json.loads(
            "".join(admin_node.execute('curl http://{}/api/status'.format(
                kibana_public_endpoint))['stdout']))
        status_overall = status_full['status']['overall']['state']
        assert status_overall == 'green', "Kibaba service have issues. " \
                                          "Status {}".format(status_overall)

    def test_logging_log_rotate_for_mysql(
            self,
            admin_node,
            k8scluster):
        """Test log rotate for mysql
                Scenario:
                1. Install k8s
                2. Install microservices
                3. Fetch all repos
                4. Build images or use external registry
                5. Deploy openstack
                6. Clean mysql log on cron pod
                7. Create mysql.log file required for log rotate in cron pod
                8. Trigger dayly cron logrotate task
                9. Repeat steps 7,8(create and trigger) for 9 times
                10. Ensure that count of log files is equal to 7
        """
        logger.info('Log rotate for mysql')
        log_path = '/var/log/ccp/mysql/'
        log_file = 'mysql.log'
        k8sclient = k8scluster.api
        # get cron pod
        cron_pod = filter(lambda x: 'cron-' in x.name, k8sclient.pods.list(
            namespace=ext.Namespace.BASE_NAMESPACE))[0]
        # clean files
        utils.rm_files(admin_node, cron_pod, log_path + log_file + '*')
        # repeat 10 days simulation create and log rotate
        for day in range(0, 10):
            utils.create_file(admin_node, cron_pod, log_path + log_file, 110)
            utils.run_daily_cron(admin_node, cron_pod, 'logrotate')
            sleep(5)

        # check logs rotation (count of rotated files not exceed 8 files)
        log_files = utils.list_files(
            admin_node, cron_pod, log_path + log_file + '*')
        assert len(log_files) == 7,\
            "Count of log files after rotation is wrong. " \
            "Expected {} Actual {}".format(log_files, 7)

    @staticmethod
    def check_message_format(event, logger):
        """Event consistency validator"""
        assert len(event['Timestamp']) > 0, \
            "Logger {} have wrong [timestamp] field".format(logger)
        assert event['Type'] == 'log', \
            "Logger {} have wrong [Type] field".format(logger)
        assert len(event['Payload']) > 0, \
            "Logger {} have wrong [Payload] field".format(logger)
        assert isinstance(event['Pid'], int), \
            "Logger {} have wrong [Pid] field".format(logger)
        assert len(event['Hostname']) > 0, \
            "Logger {} have wrong [Hostname] field".format(logger)
        assert event['severity_label'] in ext.LOG_LEVELS, \
            "Logger {} have wrong [severity_label] field".format(logger)
        assert len(event['programname']) > 0, \
            "Logger {} have wrong [programname] field".format(logger)
        assert isinstance(event['Severity'], int), \
            "Logger {} have wrong [Severity] field".format(logger)
