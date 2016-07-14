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


def check_calico_network(remote, master_node):
    k8scluster = K8sCluster(
        user=settings.KUBE_ADMIN_USER, password=settings.KUBE_ADMIN_PASS,
        host=master_node, namespace='kube-system')
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


def check_pods_status(master_node):
    k8scluster = K8sCluster(
        user=settings.KUBE_ADMIN_USER, password=settings.KUBE_ADMIN_PASS,
        host=master_node, namespace='default')
    pod_names = [pod.name for pod in k8scluster.pods.list()]
    res = [
        (k8scluster.pods.get(pod_name)._data).to_dict()['status']['phase']
        for pod_name in pod_names]
    pod_res = zip(pod_names, res)
    for pod in pod_res:
        helpers.wait(pod[1] == 'Running', timeout=300,
                     timeout_msg='Timeout waiting, not all environment pods '
                     'were in \"Running\" state {0}'.format(pod))


def check_jobs_status(master_node):
    k8scluster = K8sCluster(
        user=settings.KUBE_ADMIN_USER, password=settings.KUBE_ADMIN_PASS,
        host=master_node, namespace='default')
    job_names = [job.name for job in k8scluster.jobs.list()]
    res = [
        (k8scluster.jobs.get(job_name)._data).to_dict()['status']['succeeded']
        for job_name in job_names]
    job_res = zip(job_names, res)
    for job in job_res:
        helpers.wait(job[1] == 1, timeout=300,
                     timeout_msg='Timeout waiting, not all environment jobs '
                                 'were succeeded {0}'.format(job))
