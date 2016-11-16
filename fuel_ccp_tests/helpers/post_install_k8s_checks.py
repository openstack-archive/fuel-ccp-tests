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

import re
import json

from devops.helpers import helpers

from fuel_ccp_tests import logger


LOG = logger.logger


def check_calico_network(remote, k8sclient):
    dns_pod = [
        pod for pod in k8sclient.pods.full_list()
        if 'kubedns' in pod.name][0]
    pods_json_raw = k8sclient.pods.get(
        name=dns_pod.name, namespace=dns_pod.metadata.namespace)._data
    pods_json = pods_json_raw.to_dict()
    pod_ip = pods_json['status']['pod_ip']
    cmd = "ping -q -c1 -w10 {0}".format(pod_ip)
    helpers.wait(remote.execute(cmd)['exit_code'] == 0,
                 timeout_msg='Timeout waiting responce from node with '
                             'dns_pod {0} '.format(pod_ip))
    options = 'ipip,nat-outgoing'
    calico_options = remote.execute(
        'calicoctl pool show --ipv4')['stdout'][3].split('|')[2].strip()
    assert calico_options == options


def required_images_exists(node_name, underlay, required_images):
    """Check if there are all base containers on node

    :param node_name: string
    :param underlay: fuel_ccp_tests.managers.UnderlaySSHManager
    :param required_images: list
    """
    cmd = "docker ps --no-trunc --format '{{.Image}}'"
    result = underlay.sudo_check_call(cmd, node_name=node_name)
    images = set([x.strip() for x in result['stdout']])
    LOG.debug('Containers on node "{0}" use images: '
              '{1}'.format(node_name, images))
    # Image name could contain unpredictable Docker registry name
    # (host:port), e.g. example.net:5000/hyperkube-amd64:v1.4.1
    # Use regex to check that image (base name) is used by some container
    assert all(
        any(re.match('^([\w.-]+(:\d+)?/)?'  # Host:port (optional)
                     '{0}:\S+$'  # image name + ":" + image tag
                     .format(required_image), image)
            for image in images)
        for required_image in required_images)


def inspect_docker_containers(image_name, underlay, host_ip):
    result = None
    cmd = "docker inspect " \
          "$(docker ps --filter ancestor={image_name} --format={{{{.ID}}}})"\
        .format(image_name=image_name)
    if underlay:
        with underlay.remote(host=host_ip) as remote:
            result = remote.execute(cmd)
    if result:
        LOG.info("Inspecting running containers with name={name}: on: {node}".
                 format(name=image_name, node=host_ip))
        for container in result.stdout_json:
            raw_out = container['Config']['Labels']
            labels = json.dumps(
                {k: raw_out[k] for k in raw_out},
                indent=4,
                separators=(',', ': ')
            )
            LOG.info("Docker container {name} Labels: {labels}".format(
                name=container['Name'],
                labels=labels)
            )
