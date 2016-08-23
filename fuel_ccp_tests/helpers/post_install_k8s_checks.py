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

from devops.helpers import helpers


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
