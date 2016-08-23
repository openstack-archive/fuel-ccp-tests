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


# TODO: replace check with deployment status request
def check_pods_status(k8sclient, timeout=600, namespace='ccp'):
    def is_pod_running(cluster, pod_name, namespace=namespace):
        return lambda: (cluster.pods.get(name=pod_name, namespace=namespace)
                        ._data).to_dict()['status']['phase'] == 'Running'
    pod_names = [pod.name for pod in k8sclient.pods.list(namespace=namespace)]
    for pod_name in pod_names:
        predicate = is_pod_running(k8sclient, pod_name)
        helpers.wait(predicate, timeout=timeout,
                     timeout_msg='Timeout waiting, pod {0}'
                     'is not in \"Running\" state'.format(pod_name))


# TODO: replace check with deployment status request
def check_jobs_status(k8sclient, timeout=600, namespace='ccp'):
    def is_job_running(cluster, job_name, namespace=namespace):
        return lambda: (cluster.jobs.get(name=job_name, namespace=namespace)
                        ._data).to_dict()['status']['succeeded'] == 'Running'
    job_names = [job.name for job in k8sclient.jobs.list(namespace=namespace)]
    for job_name in job_names:
        predicate = is_job_running(k8sclient, job_name)
        helpers.wait(predicate, timeout=timeout,
                     timeout_msg='Timeout waiting job {0} '
                                 'status is not successful'.format(job_name))
