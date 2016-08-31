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
import os
import pytest

from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests.helpers import post_os_deploy_checks


LOG = logger.logger
LOG.addHandler(logger.console)


class TestServiceGlance(object):

    @pytest.mark.revert_snapshot(ext.SNAPSHOT.initial)
    @pytest.mark.glance_test
    @pytest.mark.fail_snapshot
    def test_glance_api(self, config, underlay,
                        k8scluster, ccpcluster):
        """Glance api test
        Scenario:
        1. Install k8s
        2. Install microservices
        3. Fetch all repos
        4. Build images or use external registry
        5. Deploy openstack
        6. Download test script
        7. Test glance_api with script

        Duration 60 min
        """
        k8sclient = k8scluster.get_k8sclient()

        remote = underlay.remote(host=config.k8s.kube_host)

        ccpcluster.do_fetch()
        k8scluster.create_registry(remote)
        ccpcluster.do_build('builder_push',
                            registry_address=settings.REGISTRY)
        topology_path = os.getcwd() + '/fuel_ccp_tests/templates/' \
                                      'k8s_templates/k8s_topology.yaml'
        remote.upload(topology_path, './')
        with remote.get_sudo(remote):
            ccpcluster.do_deploy(registry_address=settings.REGISTRY,
                                 deploy_config='~/k8s_topology.yaml',
                                 images_namespace=settings.IMAGES_NAMESPACE)
        post_os_deploy_checks.check_jobs_status(k8sclient, timeout=1500,
                                                namespace='ccp')
        post_os_deploy_checks.check_pods_status(k8sclient, timeout=2500,
                                                namespace='ccp')
        # run glance_api tests
        script = settings.TEMPEST_SCRIPT_PATH
        script_result = 'rally/result.json'
        remote.upload(script, './')
        script_dir = script.split('/')[-1]
        script_name = remote.execute('ls -1 {0}'.format(
            script_dir))['stdout'][0].rstrip()
        script_path = os.path.join(script_dir, script_name)
        command = [
            'chmod +x {0}'.format(script_path),
            'cd {0}; ./{1} "--regex tempest.api.image"'.format(
                script_dir, script_name),
            'test -e {0}'.format(script_result),
        ]
        for cmd in command:
            LOG.info(
                "Running command '{cmd}' on node {node_name}".format(
                    cmd=command,
                    node_name=remote.hostname
                )
            )
            result = remote.check_call(cmd, verbose=True)
            assert result['exit_code'] == 0
        remote.download(script_result, '/tmp/')
        with open('/tmp/{0}'.format(script_result.split('/')[-1]), 'r') \
                as json_path:
            data = json_path.read()
        result_dict = json.loads(data)
        if result_dict['failures'] != 0:
            raise ValueError(
                'The tempest tests were failed, number of failures is {0}, '
                'detailed log {1}:~/{2}'.format(
                    result_dict['failures'], remote.hostname, script_result))
