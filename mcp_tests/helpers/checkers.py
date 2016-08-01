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

from mcp_tests import settings
from mcp_tests.models.k8s import K8sCluster
from devops.helpers import helpers


def check_calico_network(remote, env):
    k8scluster = K8sCluster(
        user=settings.KUBE_ADMIN_USER, password=settings.KUBE_ADMIN_PASS,
        host=env.k8s_ips[0], namespace='kube-system')
    dns_pod = [
        pod.name for pod in k8scluster.pods.list() if 'kubedns' in pod.name][0]
    pods_json_raw = k8scluster.pods.get(dns_pod)._data
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


def check_pods_status(env):
    def is_pod_running(cluster, pod_name):
        return lambda: (cluster.pods.get(pod_name)
                        ._data).to_dict()['status']['phase'] == 'Running'
    k8scluster = K8sCluster(
        user=settings.KUBE_ADMIN_USER, password=settings.KUBE_ADMIN_PASS,
        host=env.k8s_ips[0], namespace='default')
    pod_names = [pod.name for pod in k8scluster.pods.list()]
    for pod_name in pod_names:
        predicate = is_pod_running(k8scluster, pod_name)
        helpers.wait(predicate, timeout=300,
                     timeout_msg='Timeout waiting, pod {0}'
                     'is not in \"Running\" state'.format(pod_name))


def check_jobs_status(env):
    def is_job_running(cluster, job_name):
        return lambda: (cluster.jobs.get(job_name)
                        ._data).to_dict()['status']['succeeded'] == 'Running'
    k8scluster = K8sCluster(
        user=settings.KUBE_ADMIN_USER, password=settings.KUBE_ADMIN_PASS,
        host=env.k8s_ips[0], namespace='default')
    job_names = [job.name for job in k8scluster.jobs.list()]
    for job_name in job_names:
        predicate = is_job_running(k8scluster, job_name)
        helpers.wait(predicate, timeout=300,
                     timeout_msg='Timeout waiting job {0} '
                                 'status is not successful'.format(job_name))
