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
from datetime import datetime
from time import sleep

import pytest

from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests.helpers import utils
from fuel_ccp_tests.logger import logger


@pytest.yield_fixture(scope='function')
def admin_node(config, underlay, ccpcluster):
    logger.info("Get SSH access to admin node")
    with underlay.remote(host=config.k8s.kube_host) as remote:
        yield remote


@pytest.yield_fixture(scope='function')
def elastic_client_public(os_deployed, k8s_actions, config):
    """
    Discover elasticsearch on the cluster and return simple elastic client
    initialized with public endpoint
    :param os_deployed:
    :param k8s_actions:
    :param config:
    :return: utils.ElasticClient
    """
    service_list = k8s_actions.api.services.list(
        namespace=ext.Namespace.BASE_NAMESPACE)
    service = [service for service in
               service_list if 'elasticsearch' in service.name][0]

    elastic_search_public_port = service.spec.ports[0].node_port
    elastic_search_public_host = config.k8s.kube_host

    yield utils.ElasticClient(elastic_search_public_host,
                              elastic_search_public_port)


@pytest.yield_fixture(scope='function')
def elastic_client_private(os_deployed,
                           k8s_actions,
                           admin_node,
                           config):
    """
    Discover elasticsearch on the cluster and return simple elastic client
    initialized with pod ip endpoint
    :param os_deployed:
    :param k8s_actions:
    :param config:
    :return: utils.ElasticClient
    """
    service_list = k8s_actions.api.services.list(
        namespace=ext.Namespace.BASE_NAMESPACE)
    service = [service for service in
               service_list if 'elasticsearch' in service.name][0]

    elastic_search_service_host = service.spec.cluster_ip
    elastic_search_service_port = service.spec.ports[0].name

    yield utils.ElasticClient(elastic_search_service_host,
                              elastic_search_service_port)


@pytest.fixture(scope='function')
def kibana_public_endpoint(os_deployed,
                           k8s_actions,
                           admin_node,
                           config):
    """
    Discover kibana on the cluster and return kibana endpoint
    :param os_deployed:
    :param k8s_actions:
    :param admin_node:
    :param config:
    :return: host:port
    """
    service_list = k8s_actions.api.services.list(
        namespace=ext.Namespace.BASE_NAMESPACE)
    service = [service for service in
               service_list if 'kibana' in service.name][0]

    kibana_public_port = service.spec.ports[0].node_port
    kibana_public_address = config.k8s.kube_host

    return '{}:{}'.format(kibana_public_address, kibana_public_port)


@pytest.mark.ccp_logging
@pytest.mark.revert_snapshot(ext.SNAPSHOT.os_deployed)
class TestCppLogging(object):
    """Check logging aggregation"""
    def test_logging_connection_to_elasticsearch_public(
            self, admin_node, elastic_client_public, show_step):
        """Elasticsearch api test
        Precondition:
        1. Install k8s
        2. Install microservices
        3. Fetch all repos
        4. Build images or use external registry
        5. Deploy openstack

        Scenario:
        1. Test elasticsearch is accessible on public ip
        """
        show_step(1)
        elastic_call = 'curl -s -o /dev/null -w "%{{http_code}}" http://{}:{}/'
        elastic_http_response = admin_node.execute(elastic_call.format(
            elastic_client_public.host,
            elastic_client_public.port))['stdout']

        assert ext.HttpCodes.OK in elastic_http_response, \
            "Elastic respond with unexpected " \
            "HTTP_RESPONSE on public endpoint Expected {} Actual {}".format(
                ext.HttpCodes.OK, elastic_http_response)

    def test_logging_connection_to_elasticsearch_private(
            self,
            admin_node,
            elastic_client_private,
            show_step):
        """Elasticsearch api test
        Precondition:
        1. Install k8s
        2. Install microservices
        3. Fetch all repos
        4. Build images or use external registry
        5. Deploy openstack

        Scenario:
        1. Test elasticsearch is accessibile on private ip
        """
        show_step(1)
        elastic_call = 'curl -s -o /dev/null -w "%{{http_code}}" http://{}:{}/'
        elastic_http_response = admin_node.execute(
            elastic_call.format(
                elastic_client_private.host,
                elastic_client_private.port))['stdout']
        assert ext.HttpCodes.OK in elastic_http_response, \
            "Elastic respond with unexpected " \
            "HTTP_RESPONSE on private endpoint Expected {} Actual {}".format(
                ext.HttpCodes.OK, elastic_http_response)

    def test_logging_search_for_logs_from_all_running_heka_instances(
            self, admin_node, k8scluster, elastic_client_public, show_step):
        """Heka connection test
        Precondition:
        1. Install k8s
        2. Install microservices
        3. Fetch all repos
        4. Build images or use external registry
        5. Deploy openstack

        Scenario:
        1. Find logs from all heka nodes
        2. Test that logs from each heka node exist
        """

        show_step(1)
        ec = elastic_client_public
        k8sclient = k8scluster.api
        # get all nodes
        nodes = k8sclient.nodes.list()
        # get all heka instances
        hekas = [pod for pod
                 in k8sclient.pods.list(namespace=ext.Namespace.BASE_NAMESPACE)
                 if 'heka' in pod.name]
        # ensure heka is running on each node
        assert len(nodes) == len(hekas)

        show_step(2)
        for heka_job in hekas:
            logger.info('Checking presense in aggregated log messages from {}'
                        .format(heka_job.name))
            assert ec.find('Hostname', heka_job.name).count > 0, \
                "Log message from heka node {} not found on elastic".format(
                    heka_job.name)

    def test_logging_trigger_event_into_mysql(self,
                                              admin_node,
                                              k8scluster,
                                              elastic_client_public,
                                              show_step):
        """Trigger event in mysql container
        Precondition:
        1. Install k8s
        2. Install microservices
        3. Fetch all repos
        4. Build images or use external registry
        5. Deploy openstack

        Scenario:
        1. Get mysql pod
        2. Trigger mysql log event inside the container
        3. Test that triggered event pushed to elasticsearch
        """
        ec = elastic_client_public
        k8sclient = k8scluster.api

        show_step(1)
        mysql_pod = [pod for pod in
                     k8sclient.pods.list(
                         namespace=ext.Namespace.BASE_NAMESPACE)
                     if 'mariadb' in pod.name][0]

        show_step(2)
        mysql_id = str(uuid.uuid4()).replace('-', '')
        mysql_template = \
            '{} 140115909998528 ' \
            '[Note] mysqld: ready for connections. {}\n'.format(
                datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
                mysql_id)

        admin_node.check_call(
            'kubectl exec {} --namespace={} -- {}'.format(
                mysql_pod.name,
                ext.Namespace.BASE_NAMESPACE,
                '\'/bin/bash\' -xc \'(echo \"{}\" >> '
                '/var/log/ccp/mysql/mysql.log)\''.format(
                    mysql_template)
            ),
            expected=[ext.ExitCodes.EX_OK])

        show_step(3)
        injected = ec.find('Payload', mysql_id)
        assert injected.count == 1, \
            "New log message from mysql from {} not picked by heka".format(
                mysql_pod)

    def test_logging_trigger_event_into_rabbitmq(self,
                                                 admin_node,
                                                 k8scluster,
                                                 elastic_client_public,
                                                 show_step):
        """Trigger event in rabbitmq container
        Precondition:
        1. Install k8s
        2. Install microservices
        3. Fetch all repos
        4. Build images or use external registry
        5. Deploy openstack

        Scenario:
        1. Get rabbitmq pod
        2. Trigger rabbitmq log event inside the container
        3. Test that triggered event pushed to elasticsearch
        """
        show_step(1)
        ec = elastic_client_public
        k8sclient = k8scluster.api
        rabbitmq_pod = [pod for pod in
                        k8sclient.pods.list(
                            namespace=ext.Namespace.BASE_NAMESPACE)
                        if 'rabbitmq' in pod.name][0]

        show_step(2)
        rabbitmq_id = str(uuid.uuid4()).replace('-', '')
        rabbitmq_template = "=INFO REPORT==== {} ===\n" \
                            "accepting AMQP connection <0.580.0> " \
                            "(10.233.83.7 -> 10.233.83.89:5672):\n" \
                            "{}".format(datetime.today()
                                        .strftime("%d-%b-%Y::%H:%M:%S"),
                                        rabbitmq_id)
        admin_node.check_call(
            'kubectl exec {} --namespace={} -- {}'.format(
                rabbitmq_pod.name,
                ext.Namespace.BASE_NAMESPACE,
                '\'/bin/bash\' -xc \'(echo -e \"{}\n\" >> '
                '/var/log/ccp/rabbitmq/rabbitmq.log)\''.format(
                    rabbitmq_template)),
            expected=[ext.ExitCodes.EX_OK])

        show_step(3)
        injected = ec.find('Payload', rabbitmq_id)
        assert injected.count == 1,\
            "New log message from mysql from {} not picked by heka".format(
                rabbitmq_pod)

    def test_logging_attributes_for_mysql_message(self,
                                                  elastic_client_public,
                                                  show_step):
        """Test attibute population consistency for mysql
        Precondition:
        1. Install k8s
        2. Install microservices
        3. Fetch all repos
        4. Build images or use external registry
        5. Deploy openstack

        Scenario:
        1. Search mysql log event in the elasticsearch
        2. Test logged message consistency
        """
        show_step(1)
        ec = elastic_client_public
        event = ec.find('Logger', 'mysql').get(0)

        show_step(2)
        self.check_message_format(event, 'mysql')

    def test_logging_attributes_for_rabbitmq_message(
            self,
            elastic_client_public,
            show_step):
        """Test attibute population consistency for rabbitmq
        Precondition:
        1. Install k8s
        2. Install microservices
        3. Fetch all repos
        4. Build images or use external registry
        5. Deploy openstack

        Scenario:
        1. Search rabbitmq log event in the elasticsearch
        2. Test logged message consistency
        """
        show_step(1)
        ec = elastic_client_public
        event = ec.find('Logger', 'rabbitmq').get(0)

        show_step(2)
        self.check_message_format(event, 'rabbitmq')

    def test_logging_attributes_for_openstack_horizon_apache_message(
            self,
            elastic_client_public,
            k8s_actions,
            admin_node,
            show_step):
        """Test attibute population consistency for horizon-apache
        Precondition:
        1. Install k8s
        2. Install microservices
        3. Fetch all repos
        4. Build images or use external registry
        5. Deploy openstack

        Scenario:
        1. Trigger horizon to produce logs
        2. Search horizon-apache log event in the elasticsearch
        3. Test logged message consistency
        """
        show_step(1)
        service_list = k8s_actions.api.services.list(
            ext.Namespace.BASE_NAMESPACE)
        service = [service for service in
                   service_list if 'horizon' in service.name][0]
        horizon_service_host = service.spec.cluster_ip
        horizon_service_port = service.spec.ports[0].name
        admin_node.check_call(
            'curl http://{}:{}'.format(horizon_service_host,
                                       horizon_service_port),
            expected=[ext.ExitCodes.EX_OK])

        show_step(2)
        ec = elastic_client_public
        event = ec.find('Logger', 'openstack.horizon-apache').get(0)

        show_step(3)
        self.check_message_format(event, 'openstack.horizon-apache')

    def test_logging_attributes_for_openstack_keystone_message(
            self,
            elastic_client_public,
            show_step):
        """Test attibute population consistency for keystone
        Precondition:
        1. Install k8s
        2. Install microservices
        3. Fetch all repos
        4. Build images or use external registry
        5. Deploy openstack

        Scenario:
        1. Search keystone log event in the elasticsearch
        2. Test logged message consistency
        """
        show_step(1)
        ec = elastic_client_public
        event = ec.find('Logger', 'openstack.keystone').get(0)

        show_step(2)
        self.check_message_format(event, 'openstack.keystone')

    def test_logging_attributes_for_openstack_keystone_apache_message(
            self,
            elastic_client_public,
            show_step):
        """Test attibute population consistency for keystone-apache
        Precondition:
        1. Install k8s
        2. Install microservices
        3. Fetch all repos
        4. Build images or use external registry
        5. Deploy openstack

        Scenario:
        1. Search keystone-apache log event in the elasticsearch
        2. Test logged message consistency
        """
        show_step(1)
        ec = elastic_client_public
        event = ec.find('Logger', 'openstack.keystone-apache').get(0)

        show_step(2)
        self.check_message_format(event, 'openstack.keystone-apache')

    def test_logging_attributes_for_openstack_nova_message(
            self,
            elastic_client_public,
            show_step):
        """Test attibute population consistency for nova
        Precondition:
        1. Install k8s
        2. Install microservices
        3. Fetch all repos
        4. Build images or use external registry
        5. Deploy openstack

        Scenario:
        1. Search nova log event in the elasticsearch
        2. Test logged message consistency
        """
        show_step(1)
        ec = elastic_client_public
        event = ec.find('Logger', 'openstack.nova').get(0)

        show_step(2)
        self.check_message_format(event, 'openstack.nova')

    def test_logging_attributes_for_openstack_neutron_message(
            self,
            elastic_client_public,
            show_step):
        """Test attibute population consistency for neutron
        Precondition:
        1. Install k8s
        2. Install microservices
        3. Fetch all repos
        4. Build images or use external registry
        5. Deploy openstack

        Scenario:
        1. Search neutron log event in the elasticsearch
        2. Test logged message consistency
        """
        show_step(1)
        ec = elastic_client_public
        event = ec.find('Logger', 'openstack.neutron').get(0)

        show_step(2)
        self.check_message_format(event, 'openstack.neutron')

    def test_logging_attributes_for_openstack_glance_message(
            self,
            elastic_client_public,
            show_step):
        """Test attibute population consistency for glance
        Precondition:
        1. Install k8s
        2. Install microservices
        3. Fetch all repos
        4. Build images or use external registry
        5. Deploy openstack

        Scenario:
        1. Search glance log event in the elasticsearch
        2. Test logged message consistency
        """
        show_step(1)
        ec = elastic_client_public
        event = ec.find('Logger', 'openstack.glance').get(0)

        show_step(2)
        self.check_message_format(event, 'openstack.glance')

    def test_logging_attributes_for_openstack_heat_message(
            self,
            elastic_client_public,
            show_step):
        """Test attibute population consistency for heat
        Precondition:
        1. Install k8s
        2. Install microservices
        3. Fetch all repos
        4. Build images or use external registry
        5. Deploy openstack

        Scenario:
        1. Search heat log event in the elasticsearch
        2. Test logged message consistency
        """
        show_step(1)
        ec = elastic_client_public
        event = ec.find('Logger', 'openstack.heat').get(0)

        show_step(2)
        self.check_message_format(event, 'openstack.heat')

    def test_logging_attributes_for_openvswitch_message(
            self,
            elastic_client_public,
            show_step):
        """Test attibute population consistency for openvswitch
        Precondition:
        1. Install k8s
        2. Install microservices
        3. Fetch all repos
        4. Build images or use external registry
        5. Deploy openstack

        Scenario:
        1. Search openvswitch log event in the elasticsearch
        2. Test logged message consistency
        """
        show_step(1)
        ec = elastic_client_public
        event = ec.find('Logger', 'openvswitch').get(0)

        show_step(2)
        self.check_message_format(event, 'openvswitch')

    def test_logging_explore_indexes_with_kibana(
            self,
            admin_node,
            kibana_public_endpoint,
            show_step):
        """Test index availability from kibana
        Precondition:
        1. Install k8s
        2. Install microservices
        3. Fetch all repos
        4. Build images or use external registry
        5. Deploy openstack

        Scenario:
        1. Get kibana service status
        2. Test overal status should be green
        """
        show_step(1)
        status_full = json.loads(
            "".join(admin_node.execute('curl http://{}/api/status'.format(
                kibana_public_endpoint))['stdout']))
        status_overall = status_full['status']['overall']['state']

        show_step(2)
        assert status_overall == 'green', "Kibaba service have issues. " \
                                          "Status {}".format(status_overall)

    def test_logging_kibana_running_single_node(
            self,
            admin_node,
            os_deployed,
            k8s_actions,
            show_step):
        """Test kibana running single node
        Precondition:
        1. Install k8s
        2. Install microservices
        3. Fetch all repos
        4. Build images or use external registry
        5. Deploy openstack

        Scenario:
        1. Check kibana running single node
        """
        show_step(1)
        pods_list = k8s_actions.api.pods.list(
            namespace=ext.Namespace.BASE_NAMESPACE)
        kibana_count = len(
            [pod for pod in pods_list
             if 'kibana' in pod.name])
        assert kibana_count == 1, "Unexpected count of kibana instances"

    def test_logging_elastic_running_single_node(
            self,
            admin_node,
            os_deployed,
            k8s_actions,
            show_step):
        """Test elasticsearch running single node
        Precondition:
        1. Install k8s
        2. Install microservices
        3. Fetch all repos
        4. Build images or use external registry
        5. Deploy openstack

        Scenario:
        1. Check elasticsearch running single node
        """
        show_step(1)
        pods_list = k8s_actions.api.pods.list(
            namespace=ext.Namespace.BASE_NAMESPACE)
        elastic_count = len(
            [pod for pod in pods_list
             if 'elasticsearch' in pod.name])
        assert elastic_count == 1, \
            "Unexpected count of elasticsearch instances"

    def test_logging_heka_running_all_nodes(
            self,
            admin_node,
            os_deployed,
            k8s_actions,
            show_step):
        """Test heka running all nodes
        Precondition:
        1. Install k8s
        2. Install microservices
        3. Fetch all repos
        4. Build images or use external registry
        5. Deploy openstack

        Scenario:
        1. Check heka running on each node
        """
        show_step(1)
        pods_list = k8s_actions.api.pods.list(
            namespace=ext.Namespace.BASE_NAMESPACE)
        nodes_list = [node.name for node in k8s_actions.api.nodes.list()]
        heka_nodes = [
            pod.spec.node_name for pod in pods_list if 'heka' in pod.name]

        assert sorted(nodes_list) == sorted(heka_nodes),\
            "Unexpected count of heka running on nodes instances"

    def test_logging_log_rotate_for_mysql(
            self,
            admin_node,
            k8s_actions,
            show_step,
            os_deployed):
        """Test log rotate for mysql
        Precondition:
        1. Install k8s
        2. Install microservices
        3. Fetch all repos
        4. Build images or use external registry
        5. Deploy openstack

        Scenario:
        1. Clean mysql log on cron pod
        2. Simulate 8 days log rotation
        3. Ensure that count of log files is equal to 7(week rotation)
        """
        logger.info('Log rotate for mysql')
        log_path = '/var/log/ccp/mysql/'
        log_file = 'mysql.log'

        show_step(1)
        # get cron pod
        cron_pod = [pod for pod in k8s_actions.api.pods.list(
            namespace=ext.Namespace.BASE_NAMESPACE)
            if 'cron-' in pod.name][0]
        # clean files
        utils.rm_files(admin_node, cron_pod, log_path + log_file + '*')

        show_step(2)
        for day in range(0, 8):
            utils.create_file(admin_node, cron_pod, log_path + log_file, 110)
            utils.run_daily_cron(admin_node, cron_pod, 'logrotate')
            sleep(5)

        show_step(3)
        log_files = utils.list_files(
            admin_node, cron_pod, log_path, log_file + '*')
        assert len(log_files) == 7,\
            "Count of log files after rotation is wrong. " \
            "Expected {} Actual {}".format(log_files, 7)

    @staticmethod
    def check_message_format(event, logger):
        """Event consistency validator"""
        assert event is not None, "No result found for {}".format(logger)
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
