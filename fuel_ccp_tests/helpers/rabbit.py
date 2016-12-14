import kombu

from fuel_ccp_tests import logger
from fuel_ccp_tests.helpers import utils

LOG = logger.logger


class RabbitClient(object):

    def __init__(self, ip, port, user='rabbitmq', password='password'):
        c = kombu.Connection("amqp://{0}:{1}@{2}:{3}//".format(user, password,
                                                               ip, port))
        c.connect()
        self.ch = c.channel()

    def list_nodes(self, remote, pod, namespace):
        output = ''.join(
            remote.execute("kubectl exec -i {} --namespace={}"
                           " -- rabbitmqctl"
                           " cluster_status".format(pod,
                                                    namespace))['stdout'])
        substring_ind = output.find('{running_nodes')
        sub_end_ind = output.find('cluster_name')
        result_str = output[substring_ind: sub_end_ind]
        num_node = result_str.count("rabbit@")
        return num_node

    def check_queue_replicated(self, queue, remote, pod, namespace):
        remote.check_call("kubectl exec -i {} --namespace={}"
                          " -- rabbitmqctl list_queues |"
                          " grep {}".format(pod, namespace,
                                            queue))

    def create_queue(self):
        test_queue = 'test-rabbit-{}'.format(utils.rand_name())
        q = kombu.Queue(test_queue, channel=self.ch, durable=False,
                        queue_arguments={"x-expires": 15 * 60 * 1000})
        q.declare()
        return test_queue

    def publish_message_to_queue(self, queue):
        uid = utils.generate_uuid()
        producer = kombu.Producer(channel=self.ch, routing_key=queue)
        producer.publish(uid)
        return {'queue': queue, 'id': uid}

    def check_queue_message(self, message):
        q = kombu.Queue(message['queue'], channel=self.ch)
        msg = q.get(True)
        assert msg.body in message['id'],\
            "Message body is {}, expected {}".format(msg.body, message['id'])

    def delete_queue(self, queue):
        q = kombu.Queue(queue, channel=self.ch)
        q.delete()
