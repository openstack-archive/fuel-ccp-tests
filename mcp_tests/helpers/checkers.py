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
        pod.name for pod in k8sclient.pods.list() if 'kubedns' in pod.name][0]
    pods_json_raw = k8sclient.pods.get(dns_pod)._data
    pods_json = pods_json_raw.to_dict
    pod_ip = pods_json['status']['pod_ip']
    cmd = "ping -q -c1 -w10 {0}".format(pod_ip)
    helpers.wait(remote.execute(cmd)['exit_code'] == 0,
                 timeout_msg='Timeout waiting responce from node with '
                             'dns_pod {0} '.format(pod_ip))
    options = 'ipip,nat-outgoing'
    calico_options = remote.execute(
        'calicoctl pool show --ipv4')['stdout'][3].split('|')[2].strip()
    assert calico_options == options


def check_pods_status(k8sclient):
    def is_pod_running(cluster, pod_name):
        return lambda: (cluster.pods.get(pod_name)
                        ._data).to_dict()['status']['phase'] == 'Running'
    pod_names = [pod.name for pod in k8sclient.pods.list()]
    for pod_name in pod_names:
        predicate = is_pod_running(k8sclient, pod_name)
        helpers.wait(predicate, timeout=300,
                     timeout_msg='Timeout waiting, pod {0}'
                     'is not in \"Running\" state'.format(pod_name))


def check_jobs_status(k8sclient):
    def is_job_running(cluster, job_name):
        return lambda: (cluster.jobs.get(job_name)
                        ._data).to_dict()['status']['succeeded'] == 'Running'
    job_names = [job.name for job in k8sclient.jobs.list()]
    for job_name in job_names:
        predicate = is_job_running(k8sclient, job_name)
        helpers.wait(predicate, timeout=300,
                     timeout_msg='Timeout waiting job {0} '
                                 'status is not successful'.format(job_name))
